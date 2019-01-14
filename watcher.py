import os
import sys
import time

from pyparsing import *
from db import session, Route, Landmark, Instruction, directions


class Watcher(object):
    running = True
    refresh_delay_secs = 10

    # Constructor
    def __init__(self, steps_file, landmark_file):
        self._cached_stamp = 0
        self.steps_filename = steps_file
        self.landmarks_filename = landmark_file
        self.step_counter = None
        self.route = None
        self.direction = None
        self.current_point = None

        # uploading city places while initializing
        self.upload_predefined_point()

    # Keep watching in a loop
    def watch(self):
        while self.running:
            try:
                # Look for changes
                self.look()
                time.sleep(self.refresh_delay_secs)
            except KeyboardInterrupt:
                print('\nDone')
                break
            except FileNotFoundError:
                # Action on file not found
                print('File not found')
            except:
                print('Unhandled error: %s' % sys.exc_info()[0])

    # Look for changes
    def look(self):
        stamp = os.stat(self.steps_filename).st_mtime
        if stamp != self._cached_stamp:
            self._cached_stamp = stamp
            # File has changed, so do something...
            print('File has been changed...\n')
            if self.on_change is not None:
                self.on_change()

    # uploading predefined city point to DB
    def upload_predefined_point(self):
        session.query(Landmark).delete()

        # setting the name and axis coordinates parse expressions
        landmark_words = Word(alphas)
        landmark_numbers = Word(nums)

        with open(self.landmarks_filename, 'r') as f:
            landmark_lines = [landmark_line.rstrip() for landmark_line in f.readlines()]

        for landmark in landmark_lines:
            words_rule = OneOrMore(Group(landmark_words))
            numbers_rule = OneOrMore(Group(landmark_numbers))

            names_words = words_rule.parseString(landmark).asList()
            coordinates = numbers_rule.searchString(landmark).asList()

            name = " ".join("%s" % word[0] for word in names_words)

            x_coordinate, y_coordinate = coordinates[0][0][0], coordinates[0][1][0]

            # saving it to the DB
            landmark = Landmark(name=name, x_coordinate=x_coordinate, y_coordinate=y_coordinate)
            session.add(landmark)
            session.commit()

    # Run actions when file is changed
    def on_change(self):
        self.step_counter = 0

        # Create new route every time we update the instructions
        self.route = Route()
        session.add(self.route)
        session.commit()

        with open(self.steps_filename, 'r') as f:
            instructions = [step_line.strip() for step_line in f.readlines() if step_line.strip()]
        self.upload_steps(instructions)

    def upload_steps(self, instructions):
        for instruction in instructions:
            self.select_step(instruction)
            self.step_counter += 1

        self.route.validated = True
        session.add(self.route)
        session.commit()
        print("All instructions are parsed and saved to DB")
        print("Waiting for new instructions...\n")

    def select_step(self, instruction):
        """
            There are instruction rules defined here which are tried to be interpreted / parsed , then validated
            and saved to the DB. We are making sequence starting from the most complicated rule to parse to the
            least complicated ones. So moving from one to another and checking them, specific function is called and
            has appropriate arguments passed to the it.
        """
        # Start step
        start_step_condition = (self.step_counter == 0 and 'start at' in instruction.lower())
        start_step_function = self.start_step
        start_step_args = (instruction,)

        # Parsing the Landmark defined instruction
        landmark_step_condition = 'go until you reach landmark' in instruction.lower()
        landmark_step_function = self.landmark_step
        landmark_step_agrs = (instruction,)

        # Parsing distance and direction expression
        distance_and_direction_expression = Word("go" + "move") + Word(alphas) + Word(nums) + Word("blocks")
        distance_and_direction_rule = OneOrMore(Group(distance_and_direction_expression))
        distance_and_direction_words = distance_and_direction_rule.searchString(instruction).asList()
        distance_and_direction_condition = True if distance_and_direction_words else False
        distance_and_direction_function = self.distance_and_direction
        distance_and_direction_args = (instruction, distance_and_direction_words)

        # Parsing distance expression
        distance_expression = Word("go" + "move") + Word(nums) + Word("blocks")
        distance_rule = OneOrMore(Group(distance_expression))
        distance_words = distance_rule.searchString(instruction).asList()
        distance_condition = True if distance_words else False
        distance_function = self.distance
        distance_args = (instruction, distance_words)

        # Parsing turn expression
        turn_expression = Word("turn") + Word(alphas)
        turn_rule = OneOrMore(Group(turn_expression))
        turn_words = turn_rule.searchString(instruction).asList()
        turn_condition = True if turn_words else False
        turn_function = self.turn
        turn_args = (turn_words)

        # sequence is needed to check starting from the most complicated to the easiest sequences to check
        # 1st argument - condition, 2nd - function namespace, 3rd - function arguments.
        condition_sequence = [
            (start_step_condition, start_step_function, start_step_args),
            (landmark_step_condition, landmark_step_function, landmark_step_agrs),
            (distance_and_direction_condition, distance_and_direction_function, distance_and_direction_args),
            (distance_condition, distance_function, distance_args),
            (turn_condition, turn_function, turn_args)
        ]

        for condition in condition_sequence:
            if condition[0]:
                condition[1](*condition[2])
                break

    def start_step(self, instruction):
        """
            :param instruction: 
            example:
            Start at (245, 161)
        """
        coordinates = nestedExpr(opener='(', closer=')').searchString(instruction).asList()
        start_x, start_y = coordinates[0][0][0], coordinates[0][0][1]
        start_x = int(start_x.replace(",", ""))
        start_y = int(start_y.replace(",", ""))

        if start_x < 0 or start_y < 0:
            self.instruction_failed(instruction)

        self.current_point = start_x, start_y
        self.create_step(
            route_id=self.route.id, step=self.step_counter, x_direction=0, y_direction=0,
            distance=0, start_x=start_x, start_y=start_y
        )

    def landmark_step(self, instruction):
        """
            :param instruction: 
            example:
            go until you reach landmark "Independence Square"
        """
        landmark_regexp = quotedString()
        landmark_rule = OneOrMore(Group(landmark_regexp))
        landmark_name = landmark_rule.searchString(instruction).asList()
        name = landmark_name[0][0][0].replace('"', "").replace("'", '')

        landmark = session.query(Landmark).filter_by(name=name).first()

        if not landmark:
            print('\nLandmark', name, 'does not exist!\n')
            self.delete_route()
            self.watch()

        if self.current_point == (landmark.x_coordinate, landmark.y_coordinate):
            return None

        current_x, current_y = self.current_point

        x_direction, y_direction = self.direction

        if not x_direction and not y_direction:
            print('I need the direction.')
            print('Correct the instructions.\n')
            self.delete_route()
            self.watch()

        condition_dict = {
            x_direction: [landmark.x_coordinate, y_direction, current_y, landmark.y_coordinate, current_x],
            y_direction: [landmark.y_coordinate, x_direction, current_x, landmark.x_coordinate, current_y],
        }

        # Checking the correctness of direction and coordinates
        for condition in condition_dict:
            if not condition:
                value = condition_dict[condition]
                if value[4] != value[0]:
                    print('You can not reach the landmark with your route')
                    print('Correct the instructions.\n')
                    self.delete_route()
                    self.watch()

                # wrong direction to landmark
                elif value[1] < 0 and value[2] < value[3] or value[1] > 0 and value[2] > value[3]:
                    print('You are moving into wrong direction.')
                    print('Correct the instructions.\n')
                    self.delete_route()
                    self.watch()

                # correct direction to landmark
                elif value[1] < 0 and value[2] > value[3] or value[1] > 0 and value[2] < value[3]:
                    distance = abs(value[3] - value[2])
                    self.create_step(
                        route_id=self.route.id, step=self.step_counter,
                        x_direction=x_direction, y_direction=y_direction, distance=distance,
                        start_x=current_x, start_y=current_y
                    )
                    self.current_point = (landmark.x_coordinate, landmark.y_coordinate)
                    break

    def distance_and_direction(self, instruction, words):
        """
            :param instruction:
            its example:
            Go / Move West 25 blocks
        """
        self.direction = directions.get(words[0][0][1])
        x_direction, y_direction = self.direction[0], self.direction[1]
        distance = int(words[0][0][2])
        self.distance_move(x_direction, y_direction, distance, instruction)

    def distance(self, instruction, words):
        """
            :param instruction: 
            example:
            Go / Move 13 blocks 
        """
        x_direction, y_direction = self.direction[0], self.direction[1]
        distance = int(words[0][0][1])
        self.distance_move(x_direction, y_direction, distance, instruction)

    def distance_move(self, x_direction, y_direction, distance, instruction):
        """
            Makes the move to the direction
        """
        x_move, y_move = x_direction * distance, y_direction * distance
        current_point_x = self.current_point[0] + x_move
        current_point_y = self.current_point[1] + y_move

        if current_point_x < 0 or current_point_y < 0:
            self.instruction_failed(instruction)

        self.create_step(
            route_id=self.route.id, step=self.step_counter,
            x_direction=x_direction, y_direction=y_direction, distance=distance,
            start_x=self.current_point[0], start_y=self.current_point[1]
        )
        self.current_point = (current_point_x, current_point_y)

    def turn(self, words):
        """
            :param instruction: 
            example:
            Turn left / right
        """
        if not self.direction:
            print("\nYou should have the direction before the turn")
            print('Please change the instructions.\n')
            self.delete_route()
            self.watch()

        directions_sequence = [(1, 0), (0, -1), (-1, 0), (0, 1)]
        sequence_index = directions_sequence.index(self.direction)

        turn_direction = words[0][1].lower()
        if turn_direction == 'left':
            direction_index = sequence_index - 1 if sequence_index > 0 else 3
        elif turn_direction == 'right':
            direction_index = sequence_index + 1 if sequence_index < 3 else 0
        self.direction = directions_sequence[direction_index]
        self.create_step(
            route_id=self.route.id, step=self.step_counter,
            x_direction=self.direction[0], y_direction=self.direction[1], distance=0,
            start_x=self.current_point[0], start_y=self.current_point[1]
        )

    @staticmethod
    def create_step(route_id, step, x_direction, y_direction, distance, start_x, start_y):
        step = Instruction(
            route=route_id, step=step, x_direction=x_direction, y_direction=y_direction,
            distance=distance, start_x=start_x, start_y=start_y
        )
        session.add(step)
        session.commit()

    def instruction_failed(self, instruction):
        print('\nInstruction', instruction, 'is failed')
        print('You can not go to the negative values.')
        print('Please change the instructions.\n')
        self.delete_route()
        self.watch()

    def delete_route(self):
        session.query(Instruction).filter(Instruction.route == self.route.id).delete()
        session.query(Route).filter(Route.id == self.route.id).delete()
        session.commit()

watch_file = 'instructions.txt'
landmarks_file = 'landmarks.txt'

watcher = Watcher(watch_file, landmarks_file)
watcher.watch()  # start watching
