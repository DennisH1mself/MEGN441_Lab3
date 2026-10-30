import math
import threading

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
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
        self.joint_state_pub = self.create_publisher(JointState, '/controller_manager/joint_states', 10)
        self._joint_state = None
        self._joint_state_lock = threading.Lock()
        self._stop_feedback = threading.Event()
        self.feedback_timer = self.create_timer(0.1, self.publish_joint_states)
        # SDK reads can block, so keep them outside the ROS executor.
        self.feedback_thread = threading.Thread(target=self.read_joint_states, daemon=True)
        self.feedback_thread.start()

    def read_joint_states(self):
        while not self._stop_feedback.is_set():
            try:
                positions = []
                for servo_id in range(1, 6):
                    reading = self.board.bus_servo_read_position(servo_id)
                    if not reading or not 0 <= reading[0] <= 1000:
                        raise ValueError(f'No valid position for servo {servo_id}')
                    # Factory URDF calibration: pulse 500 is zero; signs are reversed.
                    positions.append(math.radians((500.0 - reading[0]) * 240.0 / 1000.0))
                    if self._stop_feedback.is_set():
                        return
                state = JointState()
                state.header.stamp = self.get_clock().now().to_msg()
                state.name = [f'joint{i}' for i in range(1, 6)]
                state.position = positions
                with self._joint_state_lock:
                    self._joint_state = state
            except Exception as e:
                if not self._stop_feedback.is_set():
                    self.get_logger().warn(f'Joint feedback error: {e}', throttle_duration_sec=5.0)
            self._stop_feedback.wait(0.2)

    def publish_joint_states(self):
        with self._joint_state_lock:
            state = self._joint_state
            self._joint_state = None
        if state is not None:
            self.joint_state_pub.publish(state)

    def destroy_node(self):
        self._stop_feedback.set()
        # Do not wait indefinitely if the SDK is waiting for a servo reply.
        self.feedback_thread.join(timeout=0.5)
        return super().destroy_node()

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
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    

if __name__=="__main__":
    main()
