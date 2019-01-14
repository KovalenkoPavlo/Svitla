import sys
import time
from db import session, Route, Instruction


class Robot(object):
    """
        Every 10 seconds querying DB looking for new not completed instructions
    """
    running = True
    refresh_delay_secs = 10
    current_point = None

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
            except:
                print('Unhandled error: %s' % sys.exc_info()[0])

    # Look for changes
    def look(self):
        route = session.query(Route).filter(
            Route.completed == False, Route.validated == True).order_by(Route.id).first()
        if route:
            print('Taking a route...')
            instructions = session.query(Instruction).filter(Instruction.route == route.id).order_by(Instruction.id)
            self.steps(instructions)

    def steps(self, instructions):
        """
            going through every instruction and moving through the point
            as all the instuctions were previously validated and we have all the correct routes
            and its points we just walk over these points
        """
        for instruction in instructions:
            self.move(
                instruction.start_x, instruction.start_y,
                instruction.x_direction, instruction.y_direction,
                instruction.distance, instruction.step
            )

        print('FINISH at', self.current_point)
        route = session.query(Route).filter(Route.id == instruction.route).first()
        route.completed = True
        session.add(route)
        session.commit()
        print('\nWAITING FOR INSTRUCTIONS FROM THE DB...')

    def move(self, start_x, start_y, x_direction, y_direction, distance, step):
        """
            function for moving for certain distance in certain direction, 
            giving the endpoint coordinates
        """
        print("STEP #{}".format(step), 'current coordinate', (start_x, start_y))
        x_move, y_move = x_direction * distance, y_direction * distance
        endpoint_x = start_x + x_move
        endpoint_y = start_y + y_move
        self.current_point = (endpoint_x, endpoint_y)

robot = Robot()
robot.watch()
