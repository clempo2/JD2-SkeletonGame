from random import shuffle
from procgame.dmd import FrameLayer, GroupedLayer, MarkupFrameGenerator, PanningLayer, PushTransition, ScriptedLayer, TextLayer
from procgame.game import AdvancedMode
from procgame.highscore import generate_highscore_frames
from procgame.sound import PLAY_NOTBUSY

class Attract(AdvancedMode):
    """A mode that runs whenever the attract show is in progress."""

    def __init__(self, game, priority):
        super(Attract, self).__init__(game, priority)
        self.quick_start_button = None
        self.lampshow_keys = ['attract0', 'attract1']

        font_large = self.game.fonts['large']
        jd_text = TextLayer(128/2, 7, font_large, 'center').set_text('Judge Dredd')
        self.jd_layer = GroupedLayer(width=128, height=32, layers=[jd_text], fill_color=(0,0,0,255), opaque=True)
        self.jd_layer.transition = PushTransition(direction='south')

        self.gun_layer = self.game.animations['gun_powerup']
        self.score_layer = self.game.generate_score_layer()

        high_score_text = TextLayer(128/2, 7, font_large, 'center').set_text('High Scores')
        self.high_scores_title_layer = GroupedLayer(width=128, height=32, layers=[high_score_text], fill_color=(0,0,0,255), opaque=True)
        self.high_scores_title_layer.transition = PushTransition(direction='north')

        self.cityscape_layer = self.game.animations['cityscape']

        self.press_yellow_layer = self.button_layer('Press Yellow Button', 'for Regulation Play', direction='west')
        self.press_yellow_layer2 = self.button_layer('Press Yellow Button', 'for Regulation Play', blink_frame=5)
        self.press_green_layer = self.button_layer('Press Green Button', 'for SuperGame', direction='west')
        self.press_green_layer2 = self.button_layer('Press Green Button', 'for SuperGame', blink_frame=5)

        self.proc_splash_layer = self.game.animations['Splash']
        self.proc_splash_layer.transition = PushTransition(direction='south')

        self.font_plain = game.fonts['medium']
        self.font_bold = game.fonts['bold']
        gen = MarkupFrameGenerator(game, self.font_plain, self.font_bold)
 
        credits_frame = gen.frame_for_markup("""


#CREDITS#

[Rules]
[Gerry Stellenberg]

[Software]
[Adam Preble]
[Michael Ocean]
[Josh Kugler]
[Clement Pellerin]

[Sound and Music]
[Rob Keller]
[Jonathan Coultan]

[Dots]
[Travis Highrise]

[Special Thanks to]
[Steven Duchac]
[Rob Anthony]
""")

        self.credits_layer = PanningLayer(width=128, height=32, frame=credits_frame, origin=(0, 0), translate=(0, 1), bounce=False, numFramesDrawnBetweenMovementUpdate=2, fill_color=(0,0,0,255))
        self.judges_layer = self.game.animations['darkjudges']

        instruct_frame = MarkupFrameGenerator(game, self.font_plain, self.font_bold).frame_for_markup("""


#INSTRUCTIONS#

Start chain features
by shooting
Build Up Chain Feature
when lit

Instructions are displayed
when starting each feature

Secure blocks by shooting
lit crime scene shots

Complete JUDGE targets
to light locks

During multiball,
Left ramp lights jackpot
shoot subway to collect

To light Ultimate Challenge:
Start all chain features
Secure all blocks
Collect a multiball jackpot




""")

        self.instruct_layer = PanningLayer(width=128, height=32, frame=instruct_frame, origin=(0,0), translate=(0,1), bounce=False, numFramesDrawnBetweenMovementUpdate=7, fill_color=(0,0,0,255))

    def mode_started(self):
        if self.quick_start_button:
            # start the game right away if one of the start buttons was pressed during the game over display
            self.game.switchmonitor.start_button_active(self.quick_start_button)
            self.quick_start_button = None
            return

        super(Attract, self).mode_started()

        # Blink the start buttons in alternation to notify player about starting a game.
        self.game.lamps.startButton.schedule(schedule=0x00ff00ff, cycle_seconds=0, now=False)
        self.game.lamps.superGame.schedule(schedule=0xff00ff00, cycle_seconds=0, now=False)

        # Turn on minimal GI lamps
        self.game.enable_gi(False)
        self.game.lamps.gi01.enable()

        self.change_lampshow()
        self.display()

    def mode_stopped(self):
        self.game.lamps.startButton.enable()
        self.game.lamps.superGame.enable()
        self.game.lampctrl.stop_show()

    def display(self):
        self.showing_instructions = False
        hs_frames = generate_highscore_frames(self.game.all_highscore_categories, self.game, self.font_plain, self.font_bold, self.game.dmd_width, self.game.dmd_height)
        hs_script = [{'seconds':1.25, 'layer':FrameLayer(frame=f)} for f in hs_frames]

        self.score_layer_index = 2  # index of self.score_layer in script

        script = \
            [{'seconds':3.0, 'layer':self.jd_layer},
            {'seconds':3.0, 'layer':self.gun_layer},
            {'seconds':2.5, 'layer':self.score_layer},
            {'seconds':2.0, 'layer':self.high_scores_title_layer}] \
            + hs_script + \
            [{'seconds':4.0, 'layer':self.cityscape_layer},
            {'seconds':0.75, 'layer':self.press_yellow_layer},
            {'seconds':2.0, 'layer':self.press_yellow_layer2},
            {'seconds':0.75, 'layer':self.press_green_layer},
            {'seconds':2.0, 'layer':self.press_green_layer2},
            {'seconds':2.5, 'layer':self.score_layer},
            {'seconds':3.0, 'layer':self.proc_splash_layer},
            {'seconds':6.0, 'layer':self.credits_layer},
            {'seconds':3.0, 'layer':self.judges_layer}]

        self.layer = ScriptedLayer(width=128, height=32, script=script, opaque=True)
        self.layer.reset()

    def display_instructions(self):
        self.showing_instructions = True
        script = [{'seconds':22.5, 'layer':self.instruct_layer}]
        self.layer = ScriptedLayer(width=128, height=32, script=script, hold=True, opaque=True)
        self.layer.reset()
        self.layer.on_complete = self.display

    def button_layer(self, button_text, play_text, blink_frame=None, direction=None):
        font_medium = self.game.fonts['medium']
        press_layer = TextLayer(128/2, 8, font_medium, 'center').set_text(button_text, seconds=None, blink_frames=blink_frame)
        play_layer = TextLayer(128/2, 17, font_medium, 'center').set_text(play_text, seconds=None, blink_frames=blink_frame)
        start_layer = GroupedLayer(128, 32, [press_layer, play_layer], fill_color=(0,0,0,255), opaque=True)
        if direction:
            start_layer.transition = PushTransition(direction=direction)
        return start_layer

    def change_lampshow(self):
        shuffle(self.lampshow_keys)
        self.game.lampctrl.play_show(self.lampshow_keys[0], repeat=True)
        self.delay(name='lampshow', event_type=None, delay=10, handler=self.change_lampshow)

    def sw_fireL_active(self, sw):
        self.game.sound.play_voice('attract', action=PLAY_NOTBUSY)
        self.layer.force_next(forward=False)

    def sw_fireR_active(self, sw):
        self.game.sound.play_voice('attract', action=PLAY_NOTBUSY)
        self.layer.force_next(forward=True)

    def sw_flipperLwL_active(self, sw):
        if not self.showing_instructions:
            self.display_instructions()

    def sw_flipperLwR_active(self, sw):
        # display the final scores
        self.display() # remove instructions if applicable and reset ScriptedLayer
        self.layer.script_index = self.score_layer_index

