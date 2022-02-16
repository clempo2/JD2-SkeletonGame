from math import ceil
import os
import pinproc
import pygame.locals
from procgame.config import value_for_key_path
from procgame.dmd import FrameLayer, MarkupFrameGenerator, ScriptedLayer
from procgame.game import BasicGame, Mode, Player
from procgame.highscore import CategoryLogic, HighScoreCategory
from procgame.lamps import LampController
from procgame.modes import BallSave, BallSearch, Trough
from procgame.service import ServiceMode
from procgame.sound import SoundController
from asset_loader import AssetLoader
from my_modes.attract import Attract
from my_modes.base import BasePlay
from my_modes.deadworld import Deadworld, DeadworldTest
from my_modes.initials import JDEntrySequenceManager
from my_modes.switchmonitor import SwitchMonitor

import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

curr_file_path = os.path.dirname(os.path.abspath(__file__))
settings_path = curr_file_path + '/config/settings.yaml'
game_data_path = curr_file_path + '/config/game_data.yaml'
game_data_template_path = curr_file_path + '/config/game_data_template.yaml'
settings_template_path = curr_file_path + '/config/settings_template.yaml'

class JDServiceMode(ServiceMode):

    def mode_stopped(self):
        super(JDServiceMode, self).mode_stopped()
        self.game.service_mode_ended()


class JDPlayer(Player):
    """Keeps the progress of one player to allow the player
       to resume where he left off in a multi-player game"""

    def __init__(self, name):
        super(JDPlayer, self).__init__(name)
        self.state_tracking = {}

    def setState(self, key, val):
        self.state_tracking[key] = val

    def getState(self, key, default=None):
        return self.state_tracking.get(key, default)


class JD2Game(BasicGame):
    """Judge Dredd pinball game"""

    def __init__(self):
        super(JD2Game, self).__init__(pinproc.MachineTypeWPC)
        self.sound = SoundController(self)
        self.lampctrl = LampController(self)
        self.logging_enabled = False

        # don't use the locale, always insert commas in groups of 3 digits
        self.score_display.format_points = self.format_points

        self.load_config('config/JD.yaml')
        self.lamp_schedules = {'slow':0x00ff00ff, 'medium':0x0f0f0f0f, 'fast':0x55555555, 'on':0xffffffff, 'off':0x00000000}
        self.create_high_score_categories()

        # Assets
        asset_loader = AssetLoader(self)
        asset_loader.load_assets(curr_file_path)
        self.animations = asset_loader.animations
        self.fonts = asset_loader.fonts

        self.reset()

    # override load_config to allow pygame key names and pygame numeric keys in the key_map
    def load_config(self, path):
        # Ignore pylint warning on next line, we by-pass immediate superclass intentionally
        super(BasicGame, self).load_config(path)

        # Setup the key mappings from the config.yaml.
        # We used to do this in __init__, but at that time the
        # configuration isn't loaded so we can't peek into self.switches.
        key_map_config = value_for_key_path(keypath='keyboard_switch_map', default={})
        if self.desktop:
            for k, v in key_map_config.items():
                switch_name = str(v)
                if self.switches.has_key(switch_name):
                    switch_number = self.switches[switch_name].number
                else:
                    switch_number = pinproc.decode(self.machine_type, switch_name)
                if type(k) == str:
                    if k.startswith('K_'): # key is a pygame key name
                        key = getattr(pygame.locals, k)
                    else: # key is character
                        key = ord(k)
                elif type(k) == int:
                    if k < 10:
                        key = ord(str(k)) # digit character
                    else:
                        key = k # numbers used as bindings for specials -- for example K_LSHIFT is 304
                else:
                    raise ValueError('invalid key name in config file: ' + str(k))
                self.desktop.add_key_map(key, switch_number)

    def reset(self):
        # work-around for poor implementation of reset by the framework
        # this is important when the game is aborted with a long press to the startButton
        self.remove_all_modes()
        
        # Reset the entire game framework
        super(JD2Game, self).reset()

        # reload the settings since they might have changed in service mode
        self.load_game_settings()
        self.load_game_stats()

        # Service mode
        self.switch_monitor = SwitchMonitor(game=self)
        deadworld_test = DeadworldTest(self, 200, self.fonts['tiny7'])
        self.service_mode = JDServiceMode(self, 100, self.fonts['tiny7'], [deadworld_test])

        # Currently there are no special ball search handlers.  The deadworld
        # could be one, but running it while balls are locked would screw up
        # the multiball logic.  There is already logic in the multiball
        # to eject balls that enter the deadworld when lock isn't lit; so it
        # shouldn't be necessary to search the deadworld.  (unless a ball jumps
        # onto the ring rather than entering through the feeder.)
        self.ball_search = BallSearch(self, priority=100, countdown_time=10,
                     coils=self.ballsearch_coils, reset_switches=self.ballsearch_resetSwitches,
                     stop_switches=self.ballsearch_stopSwitches, special_handler_modes=[])
        self.disable_ball_search()
        
        # Trough
        trough_switchnames = ['trough1', 'trough2', 'trough3', 'trough4', 'trough5', 'trough6']
        early_save_switchnames = ['outlaneR', 'outlaneL']
        self.ball_save = BallSave(self, self.lamps.drainShield, 'shooterR')
        self.ball_save.disable()
        self.trough = Trough(self, trough_switchnames, 'trough6', 'trough', early_save_switchnames, 'shooterR', self.no_op_callback)
        self.trough.ball_save_callback = self.ball_save.launch_callback
        self.trough.num_balls_to_save = self.ball_save.get_num_balls_to_save
        self.ball_save.trough_enable_ball_save = self.trough.enable_ball_save

        # Instantiate basic game features
        self.attract_mode = Attract(self)
        self.base_play = BasePlay(self)
        self.deadworld = Deadworld(self, 20)

        self.shooting_again = False

        # Add the basic modes to the mode queue
        self.add_modes([self.switch_monitor, self.attract_mode, self.ball_search, self.deadworld, self.ball_save, self.trough])
        self.attract_mode.display()

        # Make sure flippers are off, especially for user initiated resets.
        self.enable_flippers(enable=False)

    #
    # Players
    #

    def create_player(self, name):
        return JDPlayer(name)

    def request_additional_player(self):
        """ attempt to add an additional player, but honor the max number of players """
        if len(self.players) < 4:
            player = self.add_player()
            self.set_status(player.name + ' added!')
        else:
            self.logger.info('Cannot add more than 4 players.')

    def getPlayerState(self, key, default=None):
        return self.current_player().getState(key, default)

    def setPlayerState(self, key, val):
        self.current_player().setState(key, val)

    def addPlayerState(self, key, delta):
        value = self.current_player().getState(key, 0)
        self.current_player().setState(key, value + delta)

    #
    # Game
    #

    def start_game(self, supergame):
        super(JD2Game, self).start_game()
        self.game_data['Audits']['Games Started'] += 1
        self.supergame = supergame
        self.remove_modes([self.attract_mode])
        self.update_lamps()

        # Add the first player
        self.add_player()
        # Start the ball.  This includes ejecting a ball from the trough.
        self.start_ball()

    def ball_starting(self):
        super(JD2Game, self).ball_starting()
        self.modes.add(self.base_play)
        self.update_lamps()

    def ball_save_start(self, num_balls_to_save, time, now, allow_multiple_saves):
        # work-around for ball_save.start() that always adds to the timer
        self.ball_save.timer = 0
        self.ball_save.start(num_balls_to_save, time, now, allow_multiple_saves)

    def launch_balls(self, balls_to_launch):
        # launch balls from the trough if it has sufficient balls, else eject additional balls from Deadworld
        trough_balls = self.trough.num_balls()
        trough_balls_to_launch = balls_to_launch if balls_to_launch <= trough_balls else trough_balls
        deadworld_balls_to_launch = balls_to_launch - trough_balls_to_launch
        if trough_balls_to_launch:
            self.trough.launch_balls(balls_to_launch, self.no_op_callback)
        if deadworld_balls_to_launch:
            self.deadworld.eject_balls(deadworld_balls_to_launch)

    # Override to create a flag signaling extra ball.
    def shoot_again(self):
        super(JD2Game, self).shoot_again()
        self.shooting_again = True

    def end_ball(self):
        self.shooting_again = False
        super(JD2Game, self).end_ball()

        self.game_data['Audits']['Avg Ball Time'] = self.calc_time_average_string(self.game_data['Audits']['Balls Played'], self.game_data['Audits']['Avg Ball Time'], self.ball_time)
        self.game_data['Audits']['Balls Played'] += 1

    def ball_ended(self):
        self.remove_modes([self.base_play])
        self.trough.drain_callback = self.no_op_callback

    def game_ended(self):
        super(JD2Game, self).game_ended()
        self.deadworld.stop_spinning()

        # High Score Stuff
        categories = self.supergame_highscore_categories if self.supergame else self.highscore_categories
        seq_manager = JDEntrySequenceManager(game=self, priority=2, categories=categories)
        seq_manager.finished_handler = self.highscore_entry_finished
        seq_manager.ready_handler = self.highscore_entry_ready_to_prompt
        self.modes.add(seq_manager)

    def set_status(self, text):
        self.dmd.set_message(text, 3)

    #
    # Modes
    #

    def add_modes(self, mode_list):
        for mode in mode_list:
            self.modes.add(mode)

    def remove_modes(self, mode_list):
        for m in mode_list:
            self.modes.remove(m)
            # cancel all delayed handlers
            m._Mode__delayed = []

    def remove_all_modes(self):
        self.remove_modes(self.modes[:])

    def send_event(self, event):
        for mode in self.modes[:]:
            handler = getattr(mode, event, None)
            if handler:
                ret = handler()
                if ret:
                    # skip lower priority modes
                    return ret

    #
    # Tilt
    #

    def tilt_warning(self, times_warned):
        self.sound.play('tilt warning')
        self.set_status('Warning')

    def slam_tilted(self):
        self.sound.fadeout_music()
        self.sound.play('slam_tilt')
        self.set_status('SLAM TILT')
        self.remove_all_modes()
        self.reset()
        self.update_lamps()

    def tilted(self):
        self.sound.fadeout_music()
        self.sound.play('tilt')
        self.set_status('TILT')

        # Kick balls out of places it could be stuck.
        if self.switches.shooterR.is_active():
            self.coils.shooterR.pulse(50)
        if self.switches.shooterL.is_active():
            self.coils.shooterL.pulse(20)

    #
    # Ball Search
    #

    def perform_ball_search(self):
        self.set_status('Ball Search!')
        self.ball_search.perform_search(5)
        if self.deadworld.num_balls_locked > 0:
            self.deadworld.perform_ball_search()
            
    def disable_ball_search(self):
        # workaround for a bug in pyprocgame's BallSearch.disable
        self.ball_search.disable()
        self.ball_search.cancel_delayed(name='ball_search_countdown')
        self.ball_search.cancel_delayed('ball_search_coil1')
        
    # Empty callback
    # Calling self.game.trough.launch_balls() with a None callback preserves the previous callback
    # to erase the callback completely, you have to pass an empty callback instead
    def no_op_callback(self):
        pass

    #
    # Settings
    #

    def load_game_settings(self):
        self.load_settings(settings_template_path, settings_path)

        self.sound.music_volume_offset = self.user_settings['Machine']['Music volume offset']
        self.sound.set_volume(self.user_settings['Machine']['Initial volume'])

        self.balls_per_game = self.user_settings['Gameplay']['Balls per game']
        self.score_display.set_left_players_justify(self.user_settings['Display']['Left side score justify'])

        num_blocks_setting = int(self.user_settings['Gameplay']['Blocks for Ultimate Challenge'])
        self.blocks_required = min(16, 4 * ceil(num_blocks_setting / 4)) # a multiple of 4 less than or equal to 16

    # workaround for procgame.service.SettingsEditor calling this method with only one argument
    def save_settings(self, filename=None):
        super(JD2Game, self).save_settings(filename if filename else settings_path)

    #
    # Stats
    #

    def load_game_stats(self):
        self.load_game_data(game_data_template_path, game_data_path)
        for category in self.all_highscore_categories:
            category.load_from_game(self)

    def calc_time_average_string(self, prev_total, prev_x, new_value):
        prev_time_list = prev_x.split(':')
        prev_time = (int(prev_time_list[0]) * 60) + int(prev_time_list[1])
        avg_game_time = int((int(prev_total) * int(prev_time)) + int(new_value)) / (int(prev_total) + 1)
        avg_game_time_min = avg_game_time/60
        avg_game_time_sec = str(avg_game_time%60)
        if len(avg_game_time_sec) == 1:
            avg_game_time_sec = '0' + avg_game_time_sec

        return_str = str(avg_game_time_min) + ':' + avg_game_time_sec
        return return_str

    def calc_number_average(self, prev_total, prev_x, new_value):
        avg_game_time = int((prev_total * prev_x) + new_value) / (prev_total + 1)
        return int(avg_game_time)

    #
    # High Scores
    #
    
    def create_high_score_categories(self):
        classic_category = HighScoreCategory()
        classic_category.game_data_key = 'ClassicHighScoreData'

        blocks_category = self.create_high_score_category('BlocksHighScoreData', 'Block Champ', 'num_blocks', ' block')
        innerLoops_category = self.create_high_score_category('InnerLoopsHighScoreData', 'Inner Loop Champ', 'best_inner_loops', ' loop')
        outerLoops_category = self.create_high_score_category('OuterLoopsHighScoreData', 'Outer Loop Champ', 'best_outer_loops', ' loop')

        self.highscore_categories = [classic_category, blocks_category, innerLoops_category, outerLoops_category]

        supergame_category = HighScoreCategory()
        supergame_category.game_data_key = 'SuperGameHighScoreData'
        supergame_category.titles = ['SuperGame Champion', 'SuperGame High Score #1', 'SuperGame High Score #2', 'SuperGame High Score #3', 'SuperGame High Score #4']
        
        self.supergame_highscore_categories = [supergame_category, blocks_category, innerLoops_category, outerLoops_category]
        
        self.all_highscore_categories = [classic_category, supergame_category, blocks_category, innerLoops_category, outerLoops_category]

    def create_high_score_category(self, key, title, state_key, suffix):
        category = HighScoreCategory()
        category.game_data_key = key
        category.titles = [title]
        category.score_for_player = lambda player: player.getState(state_key, 0)
        category.score_suffix_singular = suffix
        category.score_suffix_plural = suffix + 's'
        return category

    def highscore_entry_ready_to_prompt(self, mode, prompt):
        self.sound.play_voice('high score')
        banner_mode = Mode(game=self, priority=8)
        markup = MarkupFrameGenerator()
        tiny7 = self.fonts['tiny7']
        markup.font_plain = tiny7
        markup.font_bold = tiny7
        text = '\n[GREAT JOB]\n#%s#\n' % (prompt.left.upper()) # we know that the left is the player name
        frame = markup.frame_for_markup(markup=text, y_offset=0)
        banner_mode.layer = ScriptedLayer(width=128, height=32, script=[{'seconds':4.0, 'layer':FrameLayer(frame=frame)}])
        banner_mode.layer.on_complete = lambda: self.highscore_banner_complete(banner_mode=banner_mode, highscore_entry_mode=mode)
        self.modes.add(banner_mode)

    def highscore_banner_complete(self, banner_mode, highscore_entry_mode):
        self.remove_modes([banner_mode])
        self.update_lamps()
        highscore_entry_mode.prompt()

    def highscore_entry_finished(self, mode):
        self.remove_modes([mode])
        self.modes.add(self.attract_mode)
        self.attract_mode.game_over_display()
        self.update_lamps()

        # Handle game stats.
        for i in range(0, len(self.players)):
            game_time = self.get_game_time(i)
            self.game_data['Audits']['Avg Game Time'] = self.calc_time_average_string(self.game_data['Audits']['Games Played'], self.game_data['Audits']['Avg Game Time'], game_time)
            self.game_data['Audits']['Avg Score'] = self.calc_number_average(self.game_data['Audits']['Games Played'], self.game_data['Audits']['Avg Score'], self.players[i].score)
            self.game_data['Audits']['Games Played'] += 1

        self.save_game_data(game_data_path)

    def format_points(self, points):
        # disregard the locale, always insert commas between groups of 3 digits
        return '00' if points == 0 else '{:,}'.format(points)

    #
    # Service Mode
    #

    def start_service_mode(self):
        """ remove all existing modes that are running
            stop music, stop lamp shows, disable flippers
            then add the service mode.
        """

        self.remove_all_modes()

        self.lampctrl.stop_show()
        for lamp in self.lamps:
            lamp.disable()

        self.sound.stop_music()
        self.enable_flippers(False)
        self.modes.add(self.service_mode)

    def service_mode_ended(self):
        self.reset()
        self.update_lamps()

    #
    # Sound
    #

    def stop_all_sounds(self):
        # workaround for pyprocgame's SoundController lack of functionality
        for key in self.sound.sounds:
            self.sound.sounds[key][0].stop()
        self.sound.voice_end_time = 0

    def volume_down(self):
        volume = self.sound.volume_down()
        self.set_status('Volume Down : ' + str(volume))

    def volume_up(self):
        volume = self.sound.volume_up()
        self.set_status('Volume Up : ' + str(volume))

    #
    # lamps
    #

    def drive_lamp(self, lamp_name, style='on'):
        lamp_schedule = self.lamp_schedules[style]
        self.lamps[lamp_name].schedule(schedule=lamp_schedule, cycle_seconds=0, now=True)

    def drive_perp_lamp(self, perp_name, style='on'):
        for color in ['W', 'R', 'Y', 'G']:
            lamp_name = perp_name + color
            self.drive_lamp(lamp_name, style)

    def disable_drop_lamps(self):
        for lamp in ['dropTargetJ', 'dropTargetU', 'dropTargetD', 'dropTargetG', 'dropTargetE']:
            self.lamps[lamp].disable()

    def enable_gi(self, on):
        for gi in ['gi01', 'gi02', 'gi03', 'gi04', 'gi05']:
            if on:
                self.lamps[gi].enable()
            else:
                self.lamps[gi].disable()

def main():
    game = None
    try:
        game = JD2Game()
        game.run_loop()
    finally:
        del game

if __name__ == '__main__':
    main()
