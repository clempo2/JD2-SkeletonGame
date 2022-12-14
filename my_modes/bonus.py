from procgame.game import AdvancedMode
from procgame.sound import PLAY_FORCE

class Bonus(AdvancedMode):
    """Display end of ball bonus"""

    def mode_started(self):
        self.game.enable_flippers(enable=False)
        self.game.sound.fadeout_music()
        self.game.sound.stop_all()
        self.game.sound.play_voice('drain', PLAY_FORCE)
        self.game.base_play.display('Bonus')
        self.game.set_status(None)
        self.index = -1

        # compute everything before we start so we can easily skip to the end
        # do not show bonus items worth zero except the total
        self.bonus_items = (self.create_item('num_chain_features', 'Chain Feature', 4000) +
            self.create_item('num_hurry_ups', 'Hurry Up', 12000) +
            self.create_item('num_blocks', 'Block', 2000) +
            self.create_item('num_dark_judges', 'Dark Judge', 15000))

        total = sum(item['points'] for item in self.bonus_items)
        bonus_x = self.game.getPlayerState('bonus_x')
        if total > 0 and bonus_x > 1:
            self.bonus_items += [{'text': str(bonus_x) + 'X', 'points': None}]
            total *= bonus_x
        self.total_bonus = total

        self.bonus_items += [{'text': 'Total', 'points': total}]
        self.delay(name='show_bonus', event_type=None, delay=1.5, handler=self.show_bonus, param=0)

    def create_item(self, state, title, value):
        num = self.game.getPlayerState(state)
        return [] if num == 0 else [{'text': self.format_text(num, title), 'points': num * value}]

    def format_text(self, value, title):
        return str(value) + ' ' + title + ('s' if value > 1 else '')

    def show_bonus(self, index):
        self.index = index
        if index == len(self.bonus_items):
            self.game.base_play.display('')
            self.exit_callback()
        else:
            self.game.sound.play('bonus')
            bonus_item = self.bonus_items[index]
            self.game.base_play.display(bonus_item['text'], bonus_item['points'])
            if index == len(self.bonus_items) - 1:
                # Wait till we show the total to add the points and possibly get a Replay
                self.game.score(self.total_bonus)
            self.delay(name='show_bonus', event_type=None, delay=1.5, handler=self.show_bonus, param=index + 1)

    def sw_flipperLwL_active(self, sw):
        self.flipper_active()

    def sw_flipperLwR_active(self, sw):
        self.flipper_active()

    def flipper_active(self):
        # skip to total but only once
        len_minus_1 = len(self.bonus_items) - 1
        if self.index < len_minus_1:
            self.cancel_delayed('show_bonus')
            self.show_bonus(len_minus_1)
