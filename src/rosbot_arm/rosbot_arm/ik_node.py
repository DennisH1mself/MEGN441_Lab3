import rclpy
from rclpy.node import Node
from rosbot_msgs.msg import IKTarget, JointControl
import numpy as np
from arm_test import atp, pta

##  Joint Links ##
# l0 refers to the height of the arm base wrt base_link
l0 = 0.05 + 0.0654868 + 0.0338648 + 0.0772047
l1 = 0.130
l2 = 0.130
l3 = 0.055
tool_link = 0.117

lengths = [l0, l1, l2, l3+tool_link, 0]


arm_ids = [1, 2, 3, 4, 5]

# Only joint 2 is limited to protect the screen
min_pulses = [0, 125, 0, 0, 0]
max_pulses = [1000, 775, 1000, 1000, 1000]
min_angles = [-120, -90, -120, -120, -120]
max_angles = [120, 66, 120, 120, 120]



# All joints operate in the range -120 to 120 with a pulse width range of 0 to 1000

# TODO: Write helper scripts to convert from one to the other.


    
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
        x = msg.x
        y = msg.y
        z = msg.z
        roll = msg.roll
        pitch = msg.pitch
        gripper = msg.gripper
        response = JointControl()
        response.rotation, response.joint1, response.joint2, response.joint3, response.wrist = self.inverse_kinematics(x, y, z, roll, pitch)
        response.gripper = gripper
        self.publisher.publish(response)
    def inverse_kinematics(self, x, y, z, roll, pitch):
        rotation = np.rad2deg(np.arctan2(self.y, self.x))
        # vector 3
        v3z = z - (l3 + tool_link) * np.sin(np.deg2rad(pitch))
        v3rxy = np.sqrt(x**2 + y**2) - (l3 + tool_link) * np.cos(np.deg2rad(pitch))
        v3x = v3rxy * np.cos(np.deg2rad(rotation))
        v3y = v3rxy * np.sin(np.deg2rad(rotation))
        v3 = np.array([v3x, v3y, v3z])
        theta_2 = 180 - np.rad2deg(np.arccos((l1**2 + l2**2 - np.linalg.norm(v3)**2) / (2 * l1 * l2)))
        theta_1 = np.rad2deg(np.arctan2(v3[3], np.sqrt(v3[0]**2 + v3[1]**2)) - np.arccos((l1**2 + np.linalg.norm(v3)**2 - l2**2) / (2 * l1 * np.linalg.norm(v3))))
        v2 = np.array([l1 * np.cos(np.deg2rad(theta_1)) * np.cos(np.deg2rad(rotation)), l1 * np.cos(np.deg2rad(theta_1)) * np.sin(np.deg2rad(rotation)), l1 * np.sin(np.deg2rad(theta_1))])
        v23 = v3 - v2
        theta_3 = np.rad2deg(np.arctan2(v23[2], np.sqrt(v23[0]**2 + v23[1]**2))) - pitch
        
def main():
    rclpy.init()
    ik_node = IKNode()
    rclpy.spin(ik_node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
