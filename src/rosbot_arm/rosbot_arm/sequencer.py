import rclpy
from rclpy.node import Node
from tf2_ros import TransformListener, Buffer, TransformException
from rclpy.time import Time
from geometry_msgs.msg import PointStamped
from tf2_geometry_msgs import do_transform_point
from rosbot_msgs.msg import BlockDetection

class Sequencer(Node):
    def __init__(self):
        super().__init__('sequencer')
        self.get_logger().info("Sequencer node started")
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.blocks = {}
        self.subscriber = self.create_subscription(BlockDetection, '/block_detector/block_detections', self.block_callback, 10)
    def block_callback(self, msg):
        camera_point = PointStamped()
        camera_point.header = msg.header
        camera_point.point = msg.position

        try:
            transform = self.tf_buffer.lookup_transform('base_footprint', msg.header.frame_id, Time.from_msg(msg.header.stamp))
            base_point = do_transform_point(camera_point, transform)
        except TransformException as e:
            self.get_logger().warn(f"Transform error: {e}")
            return

        self.blocks[msg.color] = base_point

        p = base_point.point
        self.get_logger().info(
            f'{msg.color}: x={p.x:.3f}, y={p.y:.3f}, z={p.z:.3f} m'
        )
def main():
    rclpy.init()
    node = Sequencer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()