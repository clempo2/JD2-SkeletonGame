import time
from procgame.dmd import Frame, LayerTransitionBase, TextLayer

class FixedSizeTextLayer(TextLayer):
    """A TextLayer where the text and blank blinking frames are opaque over the whole fixed width x height"""

    def __init__(self, x, y, font, justify='left', opaque=False, width=128, height=32, fill_color=None):
        super(FixedSizeTextLayer, self).__init__(x, y, font, justify, opaque, width, height, fill_color)
        self.blank_frame = Frame(width, height)

    def set_text(self, text, seconds=None, blink_frames=None):
        """Displays the given message for the given number of seconds."""
        self.started_at = None
        self.seconds = seconds
        self.blink_frames = blink_frames
        self.blink_frames_counter = self.blink_frames

        if text == None:
            self.frame = None
        else:
            (w, h) = self.font.size(text)
            if self.justify == 'right':
                (x, y) = (self.width - w, 0)
                (self.target_x_offset, self.target_y_offset) = (-self.width, 0)
            elif self.justify == 'center':
                (x, y) = ((self.width - w)/2, 0)
                (self.target_x_offset, self.target_y_offset) = (-self.width/2, 0)
            else: # left justified
                (x, y) = (0,0)
                (self.target_x_offset, self.target_y_offset) = (0, 0)

            self.set_target_position(self.x, self.y)
            self.frame = Frame(width=self.width, height=self.height)
            if self.fill_color != None:
                self.frame.fill_rect(0, 0, self.width, self.height, self.fill_color)
            self.font.draw(self.frame, text, x, y)

        return self

    def next_frame(self):
        if self.started_at == None:
            self.started_at = time.time()
        if (self.seconds != None) and ((self.started_at + self.seconds) < time.time()):
            self.frame = None
        elif self.blink_frames > 0:
            if self.blink_frames_counter == 0:
                self.blink_frames_counter = self.blink_frames
                if self.frame == self.blank_frame:
                    self.frame = self.frame_old
                else:
                    self.frame_old = self.frame
                    self.frame = self.blank_frame
            else:
                self.blink_frames_counter -= 1
        return self.frame


class SlideTransition(LayerTransitionBase):
    """A transition that scrolls the to_frame over a blank frame"""

    def __init__(self, direction='north'):
        super(SlideTransition, self).__init__()
        self.direction = direction
        self.progress_per_frame = 1.0/20.0

    def next_frame(self, from_frame, to_frame):
        blank_frame = Frame(to_frame.width, to_frame.height)
        return super(SlideTransition, self).next_frame(blank_frame, to_frame)

    def transition_frame(self, from_frame, to_frame):
        frame = Frame(width=to_frame.width, height=to_frame.height)
        prog = -self.progress if self.in_out == 'out' else 1.0 - self.progress
        dst_x, dst_y = {
         'north': (0,  prog*frame.height),
         'south': (0, -prog*frame.height),
         'east':  (-prog*frame.width, 0),
         'west':  ( prog*frame.width, 0)
        }[self.direction]
        Frame.copy_rect(dst=frame, dst_x=dst_x, dst_y=dst_y, src=to_frame, src_x=0, src_y=0, width=frame.width, height=frame.height, op='copy')
        return frame


class DontMoveTransition(LayerTransitionBase):
    """A transition that does not move, this can be useful within a GroupedTransition"""
    def transition_frame(self, from_frame, to_frame):
        return to_frame

class GroupedTransition(LayerTransitionBase):
    """A transition that runs multiple transitions one after the other"""

    def __init__(self, transitions):
        super(GroupedTransition, self).__init__()
        if transitions is None or not transitions:
            raise Exception('List of transitions cannot be empty')
        self.transitions = transitions
        self.current = 0

    def start(self):
        self.reset()
        self.transitions[self.current].start()

    def reset(self):
        self.current = 0
        self.transitions[self.current].reset()

    def pause(self):
        self.transitions[self.current].pause()

    def next_frame(self, from_frame, to_frame):
        transition = self.transitions[self.current]
        if transition.progress_mult:
            prog = max(0.0, min(1.0, transition.progress + transition.progress_mult * transition.progress_per_frame))
            if prog >= 1.0:
                # run the next transition
                if self.current < len(self.transitions) - 1:
                    self.current += 1
                    transition = self.transitions[self.current]
                    transition.start()
                elif self.completed_handler != None:
                    self.completed_handler()
        return transition.next_frame(from_frame, to_frame)

    def transition_frame(self, from_frame, to_frame):
        return self.transitions[self.current].transition_frame(from_frame, to_frame)
