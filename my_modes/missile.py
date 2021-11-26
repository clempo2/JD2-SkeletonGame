from procgame.dmd import GroupedLayer, TextLayer
from procgame.game import Mode
from random import randint
from videomode import ShootingGallery

class MissileAwardMode(Mode):
	"""Choose an award while the ball sits in the left shooter lane"""
	
	def __init__(self, game, priority):
		super(MissileAwardMode, self).__init__(game, priority)

		self.video_mode_setting = self.game.user_settings['Gameplay']['Video mode']
		if self.video_mode_setting != "off":
			self.video_mode = ShootingGallery(self.game, priority + 11, self.video_mode_setting)
			self.video_mode.on_complete = self.video_mode_complete
		
		self.initial_awards = ['Light Extra Ball', 'Advance Crime Scenes', '30000 Points', 'Bonus +1X', 'Hold Bonus X']
		self.repeatable_award = [False, True, True, True, False]
		self.current_award_ptr = 0

		self.delay_time = 0.200
		self.active = False
		
		font = self.game.fonts['tiny7']
		self.title_layer = TextLayer(128/2, 7, font, "center")
		self.title_layer.set_text("Missile Award")

		self.element_layer = TextLayer(128/2, 15, font, "center")
		self.element_layer.set_text("Left Fire btn collects:")

		self.value_layer = TextLayer(128/2, 22, font, "center")
		self.selection_layer = GroupedLayer(128, 32, [self.title_layer, self.element_layer, self.value_layer])

	def mode_started(self):
		player = self.game.current_player()
		self.video_mode_lit = player.getState('video_mode_lit', self.video_mode_setting != "off")
		self.missile_award_lit = player.getState('missile_award_lit', False)
		self.available_awards = player.getState('available_awards', self.initial_awards[:])

	def mode_stopped(self):
		player = self.game.current_player()
		player.setState('video_mode_lit', self.video_mode_lit)
		player.setState('missile_award_lit', self.missile_award_lit)
		player.setState('available_awards', self.available_awards)

	# must be called when the missile award mode is stopped
	def reset(self):
		self.game.setState('missile_award_lit', False)

	def light_missile_award(self):
		self.missile_award_lit = True
		self.update_lamps()

	def sw_shooterL_active_for_500ms(self, sw):
		if self.missile_award_lit:
			self.missile_award_lit = False
			self.game.sound.stop_music()
			if self.video_mode_lit:
				# first award is always video if video mode is enabled in the settings
				self.game.modes.add(self.video_mode)
				self.video_mode_lit = False
			else:
				self.start_selection()
		else:
			self.missile_award_lit = True
			self.game.coils.shooterL.pulse()

	def sw_fireL_active(self, sw):
		if self.active:
			self.timer = 3
		else:
			self.game.coils.shooterL.pulse(50)

	def start_selection(self):
		self.rotate_awards()
		self.layer = self.selection_layer
		self.timer = 70
		self.active = True
		self.delay(name='missile_update', event_type=None, delay=self.delay_time, handler=self.update)

	def update(self):
		if self.timer == 0:
			self.active = False
			self.layer = None
		elif self.timer == 3:
			self.game.coils.shooterL.pulse()
			self.award()
		elif self.timer > 10:
			self.rotate_awards()
			
		if self.timer > 0:
			self.delay(name='missile_update', event_type=None, delay=self.delay_time, handler=self.update)
			self.timer -= 1

	def rotate_awards(self):
		self.self.current_award_ptr = (self.current_award_ptr + randint(1,4)) % len(self.available_awards)
		self.value_layer.set_text(self.available_awards[self.current_award_ptr])

	def award(self):
		self.game.sound.play_music('background', loops=-1)
		award = self.available_awards[self.current_award_ptr]
		if award.endswith('Points', 0) != -1:
			award_words = award.rsplit(' ')
			self.game.score(int(award_words[0]))
			self.game.base_play.show_on_display(str(award_words[0]) + ' Points', None, 'mid')
			self.game.set_status(award)
		elif award == 'Light Extra Ball':
			self.game.base_play.light_extra_ball()
		elif award == 'Advance Crime Scenes':
			self.crime_scenes.level_complete()
			self.game.base_play.show_on_display('Crimes Adv', None, 'mid')
		elif award == 'Bonus +1X':
			self.game.base_play.inc_bonus_x()
		elif award == 'Hold Bonus X':
			self.game.base_play.hold_bonus_x()

		if not self.repeatable_award[self.current_award_ptr]:
			self.available_awards[self.current_award_ptr] = str(10000*(self.current_award_ptr + 1)) + ' Points'

	def update_lamps(self):
		style = 'medium' if self.missile_award_lit else 'off'
		self.game.drive_lamp('airRaid', style)
		
	def video_mode_complete(self, success):
		self.game.sound.stop_music()
		self.game.sound.play_music('background', loops=-1)
		self.game.modes.remove(self.video_mode)
		self.game.coils.shooterL.pulse()
		if success:
			self.game.base_play.light_extra_ball()