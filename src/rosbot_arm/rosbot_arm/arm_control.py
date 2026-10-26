import rclpy
from rclpy.node import Node
from ros_robot_controller.ros_robot_controller_sdk import Board
from rosbot_msgs.msg import JointControl
from rosbot_msgs.srv import GetJointAngle

class ArmControl(Node):
    def __init__(self):
        super().__init__('arm_control')
        self.board = Board()
        self.board.enable_reception()
        self.subscriber = self.create_subscription(JointControl, '/joint_control', self.arm_control_callback, 10)
        self.service = self.create_service(GetJointAngle, '/get_joint_angle', self.get_joint_angle_callback)
    def get_joint_angle_callback(self, request, response):
        reading = self.board.bus_servo_read_position(request.joint_id)
        response.angle = pta(float(reading[0]))
        return response
    def warn(self, msg):
        self.get_logger().warn(msg)
    def arm_control_callback(self, msg):
        angles = [
            msg.rotation,
            msg.joint1,
            msg.joint2,
            msg.joint3,
            msg.wrist
        ]

        if not all(-120 <= angle <= 120 for angle in angles):
            self.warn("Out of bounds angle detected")
            return
        if not -90 <= msg.joint1 <= 66:
            self.warn("Servo 2 must be between -90 and 66 degrees")
            return
        if not 0 <= msg.gripper < 650:
            self.warn("Gripper pulse must be between 0 and 649")
            return
        targets = [
            (i, atp(angle)) for i, angle in enumerate(angles, start=1)
        ]
        targets.append((10, msg.gripper))
        duration = 1.0 # Time to complete motion
        self.board.bus_servo_set_position(duration, targets)

def atp(angle):
    return round((angle + 120) * 1000 / 240)
def pta(pulse):
    return round(pulse * 240.0 / 1000.0 - 120.0)

def main():
    rclpy.init()
    node = ArmControl()
    rclpy.spin(node)
    rclpy.shutdown()
    

if __name__=="__main__":
    main()
