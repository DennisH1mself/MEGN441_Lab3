import rclpy
from rclpy.node import Node
from rosbot_msgs.msg import IKTarget, JointControl
import numpy as np

##  Joint Links ##
# l0 is the shoulder height above base_footprint.
l0 = 0.05 + 0.0654868 + 0.0338648 + 0.0772047
l1 = 0.130
l2 = 0.130
l3 = 0.055
tool_link = 0.117

# Servo-angle limits for IDs 1 through 5; shoulder protects the screen.
min_angles = [-120, -90, -120, -120, -120]
max_angles = [120, 66, 120, 120, 120]


def inverse_kinematics(x, y, z, roll, pitch):
    if not np.all(np.isfinite([x, y, z, roll, pitch])):
        raise ValueError('IK target must contain finite numbers.')

    radius = np.hypot(x, y)
    if radius < 1e-9:
        raise ValueError('Target is on the base axis; rotation is undefined.')
    rotation = np.rad2deg(np.arctan2(y, x))

    # Wrist center relative to the fixed shoulder; keep radial sign.
    wrist_r = radius - (l3 + tool_link) * np.cos(np.deg2rad(pitch))
    wrist_z = z - l0 - (l3 + tool_link) * np.sin(np.deg2rad(pitch))
    distance = np.hypot(wrist_r, wrist_z)
    if distance < 1e-9:
        raise ValueError('Wrist center is at the shoulder; IK is singular.')
    if distance > l1 + l2 + 1e-9 or distance < abs(l1 - l2) - 1e-9:
        raise ValueError('Target is outside the arm reach.')

    cosine = (distance**2 - l1**2 - l2**2) / (2 * l1 * l2)
    elbow = np.arccos(np.clip(cosine, -1.0, 1.0))

    # Try both elbow bends and use the first one within servo limits.
    for theta_2 in (elbow, -elbow):
        theta_1 = np.arctan2(wrist_z, wrist_r) - np.arctan2(
            l2 * np.sin(theta_2), l1 + l2 * np.cos(theta_2)
        )
        theta_3 = pitch - np.rad2deg(theta_1 + theta_2)
        # Pulse 500 is upright: geometric shoulder 90 degrees, others 0.
        # Directions checked against the robot's factory servo controller
        # and jetrover_description/urdf/arm.urdf.xacro (+y pitch axes).
        servo_angles = np.array([
            rotation, np.rad2deg(theta_1) - 90.0,
            np.rad2deg(theta_2), theta_3, roll
        ])
        servo_angles = (servo_angles + 180.0) % 360.0 - 180.0
        if np.all(servo_angles >= np.array(min_angles) - 1e-9) and np.all(
            servo_angles <= np.array(max_angles) + 1e-9
        ):
            return servo_angles

    raise ValueError('Neither elbow bend fits the calibrated servo joint limits.')


class IKNode(Node):
    def __init__(self):
        super().__init__('ik_node')
        self.subscriber = self.create_subscription(
            IKTarget, '/ik_target', self.ik_callback, 10
        )
        self.publisher = self.create_publisher(
            JointControl, '/joint_control', 10
        )
    def ik_callback(self, msg):
        try:
            if not 0 <= msg.gripper < 650:
                raise ValueError('Gripper pulse must be between 0 and 649.')
            angles = self.inverse_kinematics(
                msg.x, msg.y, msg.z, msg.roll, msg.pitch
            )
        except ValueError as error:
            self.get_logger().warn(str(error))
            return

        response = JointControl()
        response.rotation, response.joint1, response.joint2, response.joint3, response.wrist = [
            int(round(angle)) for angle in angles
        ]
        response.gripper = msg.gripper
        self.publisher.publish(response)

    def inverse_kinematics(self, x, y, z, roll, pitch):
        return inverse_kinematics(x, y, z, roll, pitch)


def main():
    rclpy.init()
    ik_node = IKNode()
    rclpy.spin(ik_node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
