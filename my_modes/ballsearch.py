from procgame.modes import BallSearch

class JDBallSearch(BallSearch):
    """Search in the Deadworld planet if the first few rounds are unsuccessful.
       Unlock a ball or give a pitty ball if still unsuccessful after about 2min
    """

    def __init__(self, game, priority, countdown_time, coils=[], reset_switches=[], stop_switches=[], enable_switch_names=[], special_handler_modes=[]):
        self.initial_countdown_time = countdown_time
        self.round = 0
        self.deadworld_search = False
        super(JDBallSearch, self).__init__(game, priority, countdown_time, coils, reset_switches, stop_switches, enable_switch_names, special_handler_modes)

    def reset(self, sw):
        self.round = 0
        self.countdown_time = self.initial_countdown_time
        self.__stop_deadworld_search()
        super(JDBallSearch, self).reset(sw)

    def stop(self,sw):
        self.__stop_deadworld_search()
        super(JDBallSearch, self).stop(sw)

    def __stop_deadworld_search(self):
        if self.deadworld_search:
            self.deadworld_search = False
            self.game.deadworld.stop_ball_search()

    def perform_search(self, completion_wait_time, completion_handler=None, silent=None):
        self.round += 1
        if self.round >= 3:
            if self.round % 2:
                self.game.coils.resetDropTarget.pulse()
            else:
                self.game.coils.tripDropTarget.pulse()

        if self.round == 1:
            # launch the subsequent rounds more quickly
            self.countdown_time = 10
        elif self.round == 3:
            # searching an empty planet should not impact the state of the game
            if self.game.deadworld.num_balls_locked == 0:
                self.deadworld_search = True
                self.game.deadworld.perform_ball_search()
        elif self.round == 10 and self.game.base_play.is_started():
            if self.game.deadworld.num_balls_locked > 0:
                # release a locked ball
                self.game.deadworld.eject_balls(1, self.game.base_play.regular_play.multiball.configure_lock)
            else:
                # give a pitty ball
                self.game.launch_balls(1, stealth=True)
        elif self.round == 20 and self.game.base_play.is_started():
            # not supposed to get here, the game is confused
            # give another pitty ball as a last resort
            self.game.launch_balls(1, stealth=True)

        # for JD2, we never want to be silent
        super(JDBallSearch, self).perform_search(completion_wait_time, completion_handler=completion_handler, silent=False)

    # When the popper coil fires, the ball cup rises, activating the opto.
    # If the popper switch was a regular reset switch, we would reset
    # everytime we fire the coil and we would always be stuck at round 1.
    # Only consider events lasting ~200ms which are too long to be the ball cup.

    def sw_popperL_active_for_200ms(self, sw):
        self.stop(sw)

    def sw_popperL_inactive(self, sw):
        if sw.time_since_change() > 0.190:
            self.reset(sw)

    def sw_popperR_active_for_200ms(self, sw):
        self.stop(sw)

    def sw_popperR_inactive(self, sw):
        if sw.time_since_change() > 0.190:
            self.reset(sw)
