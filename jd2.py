from collections import OrderedDict
import logging
from math import ceil
import os
import platform
import yaml
from procgame.dmd import font_named, FrameLayer
from procgame.game import SkeletonGame
from procgame.game.skeletongame import run_proc_game
from procgame.highscore import HighScoreCategory, get_highscore_data
from procgame.modes.service import ServiceMode
from layers import DontMoveTransition, FixedSizeTextLayer, GroupedTransition, SlideTransition
from my_modes.attract import Attract
from my_modes.ballsearch import JDBallSearch
from my_modes.base import Base
from my_modes.baseplay import BasePlay
from my_modes.deadworld import Deadworld, DeadworldTest
from my_modes.stallsearch import StallSearch
from my_modes.initials import JDEntrySequenceManager
from my_modes.switchmonitor import JDSwitchMonitor

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

curr_file_path = os.path.dirname(os.path.abspath(__file__))


class JD2Game(SkeletonGame):
    """Judge Dredd pinball game"""

    # rename the settings sections used by the framework back to simpler section names
    settings_sections = {
        'Machine': 'Machine',
        'Coils': 'Coil Strength',
        'Sound': 'Sound',
        'Gameplay': 'Gameplay',
        'Replay': 'Replay'
    }

    def __init__(self):
        super(JD2Game, self).__init__('config/JD.yaml', curr_file_path)

        self.reset_pending = False
        self.lamp_schedules = {'slow':0x00ff00ff, 'medium':0x0f0f0f0f, 'fast':0x55555555, 'on':0xffffffff, 'off':0x00000000}
        self.flashers = [x for x in self.coils if x.name.startswith('flasher')]

        # shorten time to launch balls in multiball
        self.trough.inactive_shooter_time = 0.95

        # shorten Blackout animation by removing last few frames
        self.animations['blackout'].frames = self.animations['blackout'].frames[:-2]

        # a text layer for status messages, same size and location as the status line at the bottom of the score display
        self.dmd.message_layer = self.create_message_layer()

        # Create basic modes
        self.base = Base(self, 1)
        self.attract_mode = Attract(self, 2)
        self.base_play = BasePlay(self, 3)
        self.deadworld = Deadworld(self, 20)
        self.stall_search = StallSearch(self, 99997)

        # Service mode
        deadworld_test = DeadworldTest(self, 200, self.fonts['settings-font-small'])
        self.service_mode = ServiceMode(self, 99, self.fonts['settings-font-small'], extra_tests=[deadworld_test])

        self.reset()

    def reset(self):
        self.trough.num_balls_locked = self.deadworld.num_balls_locked;

        # Reset the entire game framework
        super(JD2Game, self).reset()

        # read settings
        num_blocks_setting = int(self.user_settings['Gameplay']['Blocks for Ultimate Challenge'])
        self.blocks_required = min(16, 4 * int(ceil(num_blocks_setting / 4))) # a multiple of 4 less than or equal to 16
        self.deadworld_mod_installed = self.user_settings['Machine']['Deadworld Mod Installed']
        self.shaker_mod_installed = self.user_settings['Machine']['Shaker Mod Installed']

        self.base_play.reset()
        self.start_attract_mode()

    def safe_reset(self):
        """Schedule a reset on the next tick"""
        self.reset_pending = True

    def is_missing_balls(self):
        # It's ok to start the game with balls missing in the trough if they are locked in the planet with the deadworld mod installed
        # Beware, self.deadworld_mod_installed is not yet initialized when this method is called.
        if self.user_settings['Machine']['Deadworld Mod Installed']:
            return self.deadworld.num_balls_locked + self.trough.num_balls() < self.num_balls_total
        else:
            return super(JD2Game, self).is_missing_balls()

    def tick(self):
        super(JD2Game, self).tick()
        # it is safer to call reset here than within a mode called by the run loop 
        if self.reset_pending:
            self.reset_pending = False
            self.sound.fadeout_music()
            self.sound.stop_all()
            self.reset()

    def load_settings_and_stats(self):
        super(JD2Game, self).load_settings_and_stats()
        self.create_high_score_categories()
        for category in self.all_highscore_categories:
            category.load_from_game(self)

    def create_switch_monitor(self):
        return JDSwitchMonitor(self)

    def create_ball_search(self):
        # Currently there are no special ball search handlers.  The deadworld
        # could be one, but running it while balls are locked would screw up
        # the multiball logic.  There is already logic in the multiball
        # to eject balls that enter the deadworld when lock isn't lit; so it
        # shouldn't be necessary to search the deadworld.  (unless a ball jumps
        # onto the ring rather than entering through the feeder.)

        return JDBallSearch(self, priority=100, \
                         countdown_time=self.ballsearch_time, coils=self.ballsearch_coils, \
                         reset_switches=self.ballsearch_resetSwitches, \
                         stop_switches=self.ballsearch_stopSwitches, \
                         special_handler_modes=[])

    # Empty callback
    def no_op_callback(self):
        pass

    def service_mode_ended(self):
        # tell the crane to restow to rest position in case the crane motor was powered during service mode
        self.deadworld.power_up = True
        super(JD2Game, self).service_mode_ended()

    #
    # Layers
    #
    
    def create_message_layer(self):
        """return a text layer at the bottom of the screen where the last line of the score display normally goes"""
        layer = FixedSizeTextLayer(128/2, 32-7, font_named('Font07x5.dmd'), 'center', width=128, height=7, fill_color=(0,0,0,255))

        # slide in for 0.33s, stay still for 2s, slide out for 0.33s
        slide_in_transition = SlideTransition(direction='west')
        dont_move_transition = DontMoveTransition()
        dont_move_transition.progress_per_frame = 1.0 / 120.0
        slide_out_transition = SlideTransition(direction='west')
        slide_out_transition.in_out = 'out'

        layer.grouped_transition = GroupedTransition([slide_in_transition, dont_move_transition, slide_out_transition])
        layer.grouped_transition.completed_handler = self.message_transition_completed
        return layer

    def set_status(self, text=None, scroll=True):
        # when text is None, that effectively turns off the layer and transitions are not called
        if scroll:
            # text slides in, stays for a while and then slides out
            self.dmd.message_layer.set_text(text)
            self.dmd.message_layer.transition = self.dmd.message_layer.grouped_transition
            self.dmd.message_layer.transition.start()
        else:
            # text does not move
            self.dmd.message_layer.set_text(text, seconds=3)
            self.dmd.message_layer.transition = None

    def message_transition_completed(self):
        self.dmd.message_layer.set_text(None)

    #
    # Game
    #
    def game_started(self):
        self.supergame = self.switchmonitor.superGame_button_pressed
        super(JD2Game, self).game_started()

    def ball_save_start(self, time, now, allow_multiple_saves):
        # We assume the number of balls to save is the number of balls requested by the game,
        # so launch the balls and/or eject from the planet if applicable before calling this method.
        #
        # The framework consider the 2sec grace period is included in the ball save time
        # as evidenced by the Drain Shield lamp turning off 2sec before the timer expires.
        # This is apparent when looking at the countdown timer of a timed mode and looks like a bug.
        # By adding 2sec, we move the grace period after the ball save time,
        # and the Drain Shield light will now turn off at the time given.
        # That's the real definition of a grace period in my book.

        if time > 0:
            self.enable_ball_saver(self.num_balls_requested(), 2 + time, now, allow_multiple_saves)

    def num_balls_requested(self):
        # Return what the game considers is the number of balls in play.
        # This includes the balls that are already in play plus those pending to be launched
        # less the ones to be launched that replace balls already on the playfield (now locked or in outlane)
        # It does not count locked balls but it does count balls pending to be ejected from the planet.
        # That's because the planet immediately adds the balls to be ejected to the count of balls in play
        # without waiting for the crane to release them.
        return self.trough.num_balls_requested()

    def launch_balls(self, balls_to_launch, stealth=False, autoplunge=False):
        # launch balls from the trough if it has sufficient balls, else eject additional balls from Deadworld
        # NOTE: self.trough.num_balls() is not reliable when balls are moving in the trough, don't use it here.
        new_num_requested = self.num_balls_requested() + balls_to_launch
        num_unlocked = self.num_balls_total - self.deadworld.num_balls_locked
        if new_num_requested > num_unlocked:
            num_to_eject = new_num_requested - num_unlocked
            self.deadworld.eject_balls(num_to_eject)
            balls_to_launch -= num_to_eject
        if balls_to_launch:
            # warning: must pass a real callback since passing None preserves the previous callback
            self.trough.launch_balls(balls_to_launch, self.no_op_callback, stealth, autoplunge)

    def slam_tilt_complete(self):
        # work-around to avoid calling end_ball() and end_game() when the game is tilted
        self.b_slam_tilted = False
        self.game_tilted = False
        self.reset()

    #
    # Events
    #

    def send_event(self, event):
        for mode in self.modes[:]:
            if mode.is_started():
                handler = getattr(mode, event, None)
                if handler:
                    ret = handler()
                    if ret:
                        # skip lower priority modes
                        return ret

    #
    # High Scores
    #

    def create_high_score_categories(self):
        blocks_category = self.create_high_score_category('BlocksHighScores', 'Block Champ', 'num_blocks', ' block')
        inner_loops_category = self.create_high_score_category('InnerLoopsHighScores', 'Inner Loop Champ', 'best_inner_loops', ' loop')
        outer_loops_category = self.create_high_score_category('OuterLoopsHighScores', 'Outer Loop Champ', 'best_outer_loops', ' loop')

        supergame_category = HighScoreCategory()
        supergame_category.game_data_key = 'SuperGameHighScores'
        supergame_category.titles = ['SuperGame Champion', 'SuperGame High Score #1', 'SuperGame High Score #2', 'SuperGame High Score #3', 'SuperGame High Score #4']

        classic_category = self.highscore_categories[0]
        self.highscore_categories += [classic_category, blocks_category, inner_loops_category, outer_loops_category]
        self.supergame_highscore_categories = [supergame_category, blocks_category, inner_loops_category, outer_loops_category]
        self.all_highscore_categories = [classic_category, supergame_category, blocks_category, inner_loops_category, outer_loops_category]

    def create_high_score_category(self, key, title, state_key, suffix):
        category = HighScoreCategory()
        category.game_data_key = key
        category.titles = [title]
        category.score_for_player = lambda player: player.getState(state_key, 0)
        category.score_suffix_singular = suffix
        category.score_suffix_plural = suffix + 's'
        return category

    def create_entry_sequence_manager(self):
        categories = self.supergame_highscore_categories if self.supergame else self.highscore_categories
        return JDEntrySequenceManager(game=self, priority=2, categories=categories)

    def format_points(self, points):
        # disregard the locale, always insert commas between groups of 3 digits
        return '00' if points == 0 else '{:,}'.format(points)

    def get_highscore_data(self):
        # return data for both regulation play and supergame
        return get_highscore_data(self.all_highscore_categories)

    def generate_score_layer(self):
        frame = self.score_display.layer.next_frame()
        return FrameLayer(frame=frame.copy(), opaque=True)

    #
    # lamps
    #

    def drive_lamp(self, lamp_name, style='on'):
        lamp_schedule = self.lamp_schedules[style]
        self.lamps[lamp_name].schedule(schedule=lamp_schedule)

    def drive_perp_lamp(self, perp_name, style='on'):
        for color in ['W', 'R', 'Y', 'G']:
            lamp_name = perp_name + color
            self.drive_lamp(lamp_name, style)

    def enable_gi(self, on):
        for gi in ['gi01', 'gi02', 'gi03', 'gi04', 'gi05']:
            self.drive_lamp(gi, 'on' if on else 'off')

    def disable_drop_lamps(self):
        for lamp in ['dropTargetJ', 'dropTargetU', 'dropTargetD', 'dropTargetG', 'dropTargetE']:
            self.lamps[lamp].disable()

    def disable_all_lights(self):
        self.disableAllLamps()

        # Disable all flashers
        for flasher in self.flashers:
            flasher.disable()


if __name__ == '__main__':
    # preserve order when reading YAML files
    yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        lambda loader, node: OrderedDict(loader.construct_pairs(node)))
    yaml.add_representer(OrderedDict,
        lambda dumper, data: dumper.represent_dict(data.iteritems())) 

    if platform.system() == 'Windows':
        # Turn off the screen saver on Windows.
        # Without this the DMD also goes blank when the screen saver activates.
        import ctypes
        ES_CONTINUOUS=0x80000000 # set state remains in effect
        ES_DISPLAY_REQUIRED=0x00000002 # forces the display to be on by resetting the display idle timer.
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_DISPLAY_REQUIRED)

    run_proc_game(JD2Game)