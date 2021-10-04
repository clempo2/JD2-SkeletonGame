import locale
import procgame
from procgame import *
import os.path
	
curr_file_path = os.path.dirname(os.path.abspath( __file__ ))
voice_path = curr_file_path + "/sound/Voice/skillshot/"

class SkillShot(game.Mode):
	"""Skillshot when the ball starts"""
	def __init__(self, game, priority):
		super(SkillShot, self).__init__(game, priority)
		self.text_layer = dmd.TextLayer(128/2, 7, self.game.fonts['07x5'], "center")
		self.award_layer = dmd.TextLayer(128/2, 17, self.game.fonts['num_14x10'], "center")
		self.layer = dmd.GroupedLayer(128, 32, [self.text_layer, self.award_layer])
		self.time = 0

		self.game.sound.register_sound('good shot', voice_path+'great shot.wav')
		self.game.sound.register_sound('good shot', voice_path+'incredible shot.wav')
		self.game.sound.register_sound('good shot', voice_path+'wow thats awesome.wav')
		self.game.sound.register_sound('good shot', voice_path+'jd - do it again.wav')
		self.game.sound.register_sound('good shot', voice_path+'jd - excellent.wav')
	
	def mode_started(self):
		self.shots_hit = 0
		self.update_lamps()

	def begin(self):
		self.delay(name='skill_shot_delay', event_type=None, delay=7.0, handler=self.skill_shot_expired)
		self.update_lamps()

	def update_lamps(self):
		self.game.lamps.perp4W.schedule(schedule=0x00ff00ff, cycle_seconds=0, now=True)
		self.game.lamps.perp4R.schedule(schedule=0x00ff00ff, cycle_seconds=0, now=True)
		self.game.lamps.perp4Y.schedule(schedule=0x00ff00ff, cycle_seconds=0, now=True)
		self.game.lamps.perp4G.schedule(schedule=0x00ff00ff, cycle_seconds=0, now=True)

	def award(self):
		self.game.sound.stop('good shot')
		self.game.sound.play('good shot')
		self.shots_hit += 1
		self.game.score(self.shots_hit * 5000)
		self.text_layer.set_text("Skill Shot!",3)
		score = self.shots_hit*5000
		self.award_layer.set_text(locale.format("%d",score,True),3)
		self.cancel_delayed('skill_shot_delay')
		self.delay(name='skill_shot_delay', event_type=None, delay=3.0, handler=self.skill_shot_expired)
		self.update_lamps()

	def skill_shot_expired(self):
		# Manually cancel the delay in case this function was called
		# externally.
		self.cancel_delayed('skill_shot_delay')
		self.game.lamps.perp4W.disable()
		self.game.lamps.perp4R.disable()
		self.game.lamps.perp4Y.disable()
		self.game.lamps.perp4G.disable()
		self.game.modes.remove(self)	

	def sw_leftRollover_active(self, sw):
		#See if ball came around right loop
		if self.game.switches.topRightOpto.time_since_change() < 1:
			self.award()
