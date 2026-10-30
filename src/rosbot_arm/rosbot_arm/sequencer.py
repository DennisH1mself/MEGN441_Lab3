import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener, TransformException
from tf2_geometry_msgs import do_transform_point
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import JointState
from rosbot_msgs.msg import BlockDetection, IKTarget
from rosbot_arm.ik_node import inverse_kinematics


class Sequencer(Node):
    def __init__(self):
        super().__init__('sequencer')
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.ik_pub = self.create_publisher(IKTarget, '/ik_target', 10)
        self.subscriber = self.create_subscription(
            BlockDetection, '/block_detector/block_detections', self.block_callback, 10)
        self.joint_subscriber = self.create_subscription(
            JointState, '/controller_manager/joint_states', self.joint_callback, 10)

        self.detection = None
        self.joint_time = None
        self.accept_after = None
        self.step = 0
        self.next_step = 0
        self.pick_pitch = float(self.declare_parameter('pick_pitch', -45.0).value)
        self.return_target = IKTarget(
            x=0.18, y=0.02, z=0.3, roll=0.0, pitch=-60.0, gripper=500)
        self.timer = self.create_timer(0.1, self.update)
        self.get_logger().info('Sequencer ready: waiting for a block')

    def joint_callback(self, msg):
        self.joint_time = Time.from_msg(msg.header.stamp)
        if self.accept_after is None:
            self.accept_after = self.joint_time

    def block_callback(self, msg):
        if self.step == 0 and self.detection is None:
            self.detection = msg

    def update(self):
        if self.step == 0 and self.detection is None:
            return
        now = self.get_clock().now()
        if self.joint_time is None or (now - self.joint_time).nanoseconds > 1_000_000_000:
            self.get_logger().warn('Waiting for arm_control feedback', throttle_duration_sec=5.0)
            return

        # Timer steps replace sleeps, leaving TF and feedback callbacks free to run.
        if now.nanoseconds < self.next_step:
            return
        if self.step == 1:
            self.target.gripper = 500
            self.ik_pub.publish(self.target)
            self.get_logger().info('Closing gripper')
            self.step = 2
            self.next_step = now.nanoseconds + 2_000_000_000
        elif self.step == 2:
            self.ik_pub.publish(self.return_target)
            self.get_logger().info('Returning arm')
            self.step = 3
            self.next_step = now.nanoseconds + 10_000_000_000
        elif self.step == 3:
            self.step = 0
            self.accept_after = now
            self.get_logger().info('Ready for another block')
        else:
            msg = self.detection
            image_time = Time.from_msg(msg.header.stamp)
            if image_time < self.accept_after or (now - image_time).nanoseconds > 1_000_000_000:
                self.detection = None
                return
            point = PointStamped()
            point.header, point.point = msg.header, msg.position
            try:
                transform = self.tf_buffer.lookup_transform(
                    'base_footprint', msg.header.frame_id, image_time)
                p = do_transform_point(point, transform).point
            except TransformException as error:
                self.get_logger().warn(f'Waiting for TF: {error}', throttle_duration_sec=5.0)
                return  # Keep this image and retry on the next timer tick.
            self.detection = None
            self.target = IKTarget(
                x=p.x, y=p.y+0.02, z=p.z-0.01, roll=0.0, pitch=self.pick_pitch, gripper=0)
            try:
                for target in (self.target, self.return_target):
                    inverse_kinematics(target.x, target.y, target.z, target.roll, target.pitch)
            except ValueError as error:
                self.get_logger().warn(f'Cannot pick {msg.color}: {error}', throttle_duration_sec=5.0)
                return
            self.ik_pub.publish(self.target)
            self.get_logger().info(f'Moving to {msg.color}: x={p.x:.3f}, y={p.y:.3f}, z={p.z:.3f}')
            self.step = 1
            self.next_step = now.nanoseconds + 2_000_000_000


def main():
    rclpy.init()
    node = Sequencer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
