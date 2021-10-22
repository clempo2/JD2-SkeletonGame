from procgame import *
import locale
import random

class Crimescenes(modes.Scoring_Mode):
	"""Crime scenes mode"""
	
	def __init__(self, game, priority):
		super(Crimescenes, self).__init__(game, priority)
		self.target_award_order = [1,3,0,2,4]
		self.lamp_colors = ['G', 'Y', 'R', 'W']
		difficulty = self.game.user_settings['Gameplay']['Crimescene shot difficulty']
		if difficulty == 'easy':
			self.level_templates = [
				[2,4], [2,4], 
				[2,4], [2,4], 
				[0,2,4], [0,2,4], 
				[0,2,4], [0,2,4], 
				[0,2,4], [0,2,4], 
				[0,2,3,4], [0,2,3,4], 
				[0,2,3,4], [0,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4]
			]
			self.level_nums = [ 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5 ]
		elif difficulty == 'medium':
			self.level_templates = [
				[2,4], [2,4], 
				[2,4], [2,4], 
				[0,2,4], [0,2,4], 
				[0,2,4], [0,2,4], 
				[0,2,3,4], [0,2,3,4], 
				[0,2,3,4], [0,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4]
			]
			self.level_nums = [ 1, 1, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5 ]
		else:
			self.level_templates = [
				[0,2,4], [0,2,4], 
				[0,2,4], [0,2,4], 
				[0,1,2,3,4], [0,1,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4], 
				[0,1,2,3,4], [0,1,2,3,4]
			]
			self.level_nums = [ 1, 1, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5 ]
		self.block_war = BlockWar(game, priority+5)
		self.get_block_war_multiplier = None

	def reset(self):
		self.total_levels = 0
		self.level = 0
		self.mode = 'idle'
		self.targets = [1,0,0,0,0]
		self.complete = False
		
		self.bonus_num = 1
		self.extra_ball_levels = 4
		self.bw_shots = 1
		self.bw_shots_required = [1,1,1,1,1]
		self.num_advance_hits = 0
		self.mb_active = False
		self.update_lamps()

	def mode_started(self):
		self.reset()
		
		# restore player state
		p = self.game.current_player()
		self.level = p.getState('crimescenes_level', 0)
		self.total_levels = p.getState('crimescenes_total_levels', 0)
		self.mode = p.getState('crimescenes_mode', 'idle')
		self.targets = p.getState('crimescenes_targets', [1,0,0,0,0])
		self.complete = p.getState('crimescenes_complete', False)

		if self.mode == 'idle':
			self.init_level(0)

		self.num_advance_hits = 0
		self.update_lamps()

	def mode_stopped(self):
		# save player state
		p = self.game.current_player()
		p.setState('crimescenes_level', self.level)
		p.setState('crimescenes_total_levels', self.total_levels)
		p.setState('crimescenes_mode', self.mode)
		p.setState('crimescenes_targets', self.targets)
		p.setState('crimescenes_complete', self.complete)
		
		if self.mode == 'bonus' or self.mode == 'block_war':
			self.cancel_delayed('bonus_target')
			self.game.modes.remove(self.block_war)

		for i in range(1,6):
			for j in range(0,4):
				lampname = 'perp' + str(i) + self.lamp_colors[j]
				self.game.drive_lamp(lampname, 'off')
		for i in range(1,5):
			lampname = 'crimeLevel' + str(i)
			self.game.drive_lamp(lampname, 'off')

	####################################################
	# Lamps
	####################################################
	
	def update_lamps(self):
		if self.mode == 'block_war':
			self.update_block_war_lamps()
		elif self.mode == 'levels':
			self.update_levels_lamps()
		elif self.mode == 'bonus':
			self.update_bonus_lamps()
		elif self.mode == 'complete':
			self.update_crimescenes_complete_lamps()

	def update_levels_lamps(self):
		if self.num_advance_hits == 0:
			style = 'on' 
		elif self.num_advance_hits == 1:
			style = 'slow'
		elif self.num_advance_hits == 2:
			style = 'fast'
		else:
			style = 'off'
		self.game.drive_lamp('advanceCrimeLevel', style)
			
		for i in range(0,5):
			lamp_color_num = self.level%4
			for j in range(0,4):
				lampname = 'perp' + str(i+1) + self.lamp_colors[j]
				if self.targets[i] and lamp_color_num == j:
					self.game.drive_lamp(lampname, 'medium')
				else:
					self.game.drive_lamp(lampname, 'off')
		self.update_center_lamps()

	def update_bonus_lamps(self):
		lampname = 'advanceCrimeLevel'
		self.game.drive_lamp(lampname, 'off')

		for i in range(0,5):
			for j in range(1,len(self.lamp_colors)):
				lampname = 'perp' + str(i+1) + self.lamp_colors[j]
				if self.bonus_num == i+1:
					self.game.drive_lamp(lampname, 'medium')
				else:
					self.game.drive_lamp(lampname, 'off')
	
		self.update_center_lamps()

	def update_crimescenes_complete_lamps(self):
		for i in range(0,5):
			if self.targets[i]:
				for j in range(0,4):
					lampname = 'perp' + str(i+1) + self.lamp_colors[j]
					self.game.drive_lamp(lampname, 'off')
		self.update_center_lamps()

	def update_block_war_lamps(self):
		for i in range(0,5):
			lamp_color_num = self.level%4
			for j in range(0,4):
				lampname = 'perp' + str(i+1) + self.lamp_colors[j]
				if j < self.bw_shots_required[i]:
					self.game.drive_lamp(lampname, 'medium')
				else:
					self.game.drive_lamp(lampname, 'off')
		lampname = 'advanceCrimeLevel'
		self.game.drive_lamp(lampname, 'off')
		self.update_center_lamps()

	def update_center_lamps(self):
		# Use 4 center crimescene lamps to indicate block.
		# 4 levels per block.
		for i in range (1,5):
			#lampnum = self.level%4 + 1
			lampnum = self.level/4 + 1
			lampname = 'crimeLevel' + str(i)
			if i <= lampnum:
				self.game.drive_lamp(lampname, 'on')
			else:
				self.game.drive_lamp(lampname, 'off')

	####################################################
	# Switch Handlers
	####################################################

	def sw_threeBankTargets_active(self, sw):
		if self.mode == 'levels':
			if self.num_advance_hits == 2:	
				self.award_hit()
				self.num_advance_hits = 0
				self.update_lamps()
			else:
				self.num_advance_hits += 1
				self.update_lamps()

	def sw_topRightOpto_active(self, sw):
		#See if ball came around outer left loop
		if self.game.switches.leftRollover.time_since_change() < 1:
			self.switch_hit(0)

		#See if ball came around inner left loop
		elif self.game.switches.topCenterRollover.time_since_change() < 1.5:
			self.switch_hit(1)

	def sw_popperR_active_for_300ms(self, sw):
		self.switch_hit(2)

	def sw_leftRollover_active(self, sw):
		#See if ball came around right loop
		if self.game.switches.topRightOpto.time_since_change() < 1.5:
			self.switch_hit(3)

	def sw_topCenterRollover_active(self, sw):
		#See if ball came around right loop 
		#Give it 2 seconds as ball trickles this way.  Might need to adjust.
		if self.game.switches.topRightOpto.time_since_change() < 2:
			self.switch_hit(3)

	def sw_rightRampExit_active(self, sw):
		self.switch_hit(4)

	####################################################
	# End Switch Handlers
	####################################################

	def award_hit(self):
		for i in range(0,5):
			award_switch = self.target_award_order[i]
			if self.targets[award_switch]:
				self.switch_hit(award_switch)
				return True

	def switch_hit(self, num):
		if self.mode == 'levels':
			if self.targets[num]:
				self.game.score(1000)
				self.targets[num] = 0
				if self.all_targets_off():
					self.level_complete()
				else:
					self.game.sound.play_voice('crime')
				self.update_lamps()
		elif self.mode == 'block_war':
			if self.get_block_war_multiplier != None:
				block_war_multiplier = self.get_block_war_multiplier() + 1
			else:
				block_war_multiplier = 1
			if self.bw_shots_required[num] > 0:
				self.bw_shots_required[num] -= 1
				self.block_war.switch_hit(num, self.bw_shots_required[num], block_war_multiplier)
			if self.all_bw_shots_hit():
				self.finish_level_complete()
			else:
				self.game.sound.play_voice('good shot')
				self.update_lamps()
		elif self.mode == 'bonus':
			if num+1 == self.bonus_num:
				self.cancel_delayed('bonus_target')
				self.finish_level_complete()

	def all_bw_shots_hit(self):
		for i in range(0,5):
			if self.bw_shots_required[i]:
				return False
		return True

	def setup_bw_shots_required(self, num):
		for i in range(0,5):
			self.bw_shots_required[i] = num

	def end_mb(self):
		self.cancel_delayed('bonus_target')
		self.game.modes.remove(self.block_war)
		self.mode = 'levels'
		self.level += 1
		self.init_level(self.level)
		self.mb_end_callback()

	def level_complete(self, num_levels = 1):
		self.num_levels_to_advance = num_levels
		self.finish_level_complete()

	def start_bonus(self):
		self.mode = 'bonus'
		#Play sound, lamp show, etc
		self.bonus_num = 1
		self.bonus_dir = 'up'
		self.delay(name='bonus_target', event_type=None, delay=3, handler=self.bonus_target)
		self.game.sound.play_voice('jackpot is lit')
		self.update_lamps()

	def finish_level_complete(self):
		self.game.score(10000)
		self.game.lampctrl.play_show('advance_level', False, self.game.update_lamps)
		if self.mode == 'bonus':
			self.mode = 'block_war'
			if self.bw_shots < 4:
				self.bw_shots += 1
			self.setup_bw_shots_required(self.bw_shots)
			self.block_war.bonus_hit()
			#Play sound, lamp show, etc

		elif self.mode == 'block_war':
			self.start_bonus()
		else:
			self.total_levels += self.num_levels_to_advance
			for number in range(0,self.num_levels_to_advance):
				if self.level + number == self.extra_ball_levels:
					self.light_extra_ball_function()
					break
			if (self.level % 4) == 3:
				# ensure flippers are enabled.  
				# This is a workaround for when a mode is 
				# starting (flippers disable during
				# intro) just before block wars is started.
				self.game.enable_flippers(True) 
				self.game.modes.add(self.block_war)
				self.mode = 'block_war'
				self.bw_shots = 1
				self.setup_bw_shots_required(self.bw_shots)
				self.game.trough.launch_balls(1, self.block_war_start_callback)
				self.mb_start_callback()
			else:
				self.display_level_complete(self.level,10000)
				self.level += self.num_levels_to_advance
				self.game.sound.play_voice('block complete ' + str(self.level))
				self.init_level(self.level)
				#Play sound, lamp show, etc

	def display_level_complete(self, level, points):
		self.title_layer = dmd.TextLayer(128/2, 7, self.game.fonts['07x5'], "center").set_text("Advance Crimescene", 1.5);
		self.level_layer = dmd.TextLayer(128/2, 14, self.game.fonts['07x5'], "center").set_text("Level " + str(level + 1) + " complete", 1.5);
		self.award_layer = dmd.TextLayer(128/2, 21, self.game.fonts['07x5'], "center").set_text("Award: " + locale.format("%d",points,True) + " points", 1.5);
		self.layer = dmd.GroupedLayer(128, 32, [self.title_layer, self.level_layer, self.award_layer])

	def is_multiball_active(self):
		return self.mode == 'block_war' or self.mode == 'bonus'

	def block_war_start_callback(self):
		ball_save_time = self.game.user_settings['Gameplay']['Block Wars ballsave time']
		# 1 ball added already from launcher.  So ask ball_save to save
		# new total of balls in play.
		local_num_balls_to_save = self.game.trough.num_balls_in_play
		self.game.ball_save.start(num_balls_to_save=local_num_balls_to_save, time=ball_save_time, now=False, allow_multiple_saves=True)

	def bonus_target(self):
		if self.bonus_num == 5:
			self.bonus_dir = 'down'

		if self.bonus_dir == 'down' and self.bonus_num == 1:
			self.mode = 'block_war'
			self.setup_bw_shots_required(self.bw_shots)
		else:
			if self.bonus_dir == 'up':
				self.bonus_num += 1
			else:
				self.bonus_num -= 1
			self.delay(name='bonus_target', event_type=None, delay=3, handler=self.bonus_target)
		self.update_lamps()

	def all_targets_off(self):
		for i in range(0,5):
			if self.targets[i]:
				return False
		return True

	def init_level(self, level):
		if level > (self.game.user_settings['Gameplay']['Crimescene levels for finale']-1):
			self.complete = True
			self.crimescenes_completed()
			self.mode = 'complete'
		else:
			self.mode = 'levels'
			level_template = self.level_templates[level]
			random.shuffle(level_template)
			# First initialize targets (redundant?)
			for i in range(0,5):
				self.targets[i] = 0
			# Now fill targets according to shuffled template
			for i in range(0,5):
				if i < self.level_nums[level] and i < len(self.level_templates[level]):
					self.targets[level_template[i]] = 1
		self.update_lamps()

	def complete(self):
		return self.complete

	def get_info_layers(self):
		self.title_layer = dmd.TextLayer(128/2, 7, self.game.fonts['tiny7'], "center").set_text('Crimescenes')
		self.item_0_layer = dmd.TextLayer(128/2, 16, self.game.fonts['tiny7'], "center").set_text('Current Level: ' + str(self.level + 1) + '/16')
		self.value_0_layer = dmd.TextLayer(128/2, 25, self.game.fonts['tiny7'], "center").set_text('Block War in ' + str(4-(self.level % 4)) + ' levels')

		self.layer_0 = dmd.GroupedLayer(128, 32, [self.title_layer, self.item_0_layer, self.value_0_layer])

		return [self.layer_0]
		
class BlockWar(game.Mode):
	"""Multiball activated by crime scenes"""
	def __init__(self, game, priority):
		super(BlockWar, self).__init__(game, priority)
		self.countdown_layer = dmd.TextLayer(128/2, 7, self.game.fonts['jazz18'], "center")
		self.banner_layer = dmd.TextLayer(128/2, 7, self.game.fonts['jazz18'], "center")
		self.score_reason_layer = dmd.TextLayer(128/2, 7, self.game.fonts['07x5'], "center")
		self.score_value_layer = dmd.TextLayer(128/2, 17, self.game.fonts['07x5'], "center")
		self.anim_layer = self.game.animations['blockwars']
		self.layer = dmd.GroupedLayer(128, 32, [self.anim_layer, self.countdown_layer, self.banner_layer, self.score_reason_layer, self.score_value_layer])
	
	def mode_started(self):
		self.banner_layer.set_text("Block War!", 3)
		self.game.sound.play_voice('block war start')

	def switch_hit(self, shot_index, num_remaining, multiplier):
		score = 5000 * multiplier
		self.score_value_layer.set_text(str(score), 2)
		self.game.score(score)
		self.game.sound.play('block_war_target')
		if num_remaining == 0:
			self.score_reason_layer.set_text("Block " + str(shot_index+1) + " secured!", 2)
		#if shot_index == 0:
		#	self.banner_layer.set_text("Pow!", 2)
		#if shot_index == 1:
		#	self.banner_layer.set_text("Bam!", 2)
		#if shot_index == 2:
		#	self.banner_layer.set_text("Boom!", 2)
		#if shot_index == 3:
		#	self.banner_layer.set_text("Zowie!", 2)
		#if shot_index == 4:
		#	self.banner_layer.set_text("Poof!", 2)

	def bonus_hit(self):
		self.banner_layer.set_text("Jackpot!", 2)
		self.game.sound.play_voice('jackpot')
		self.game.score(500000)

	def mode_stopped(self):
		pass
