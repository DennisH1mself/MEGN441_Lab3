# Lab 3: Robot Arm Pick and Place

## Lab Overview

In Lab 3, we will park our robots and get the arm working to pick and place colored blocks into a stack. You'll progressively step further back in arm control, starting by directly controlling the arm, then sending forward angles to a topic, and finally sending a desired end-effector position to the robot.

By the end of this lab, you'll be able to:

- Interface with the Rosbot's internal controller
- Write your own ROS2 messages and services
- Control an arm using forward kinematic commands
- Implement analytical inverse kinematics to send a gripper to a given position/orientation
- Use computer vision to detect a block using the depth camera.

### Lab Procedure

0. **Prepare the bot**: Create a clean workspace on the robot for your team for this project. Something like: `a9_ws_lab3` for team A9. You won't need any of the base ros2_ws packages - those are all in ~/ros2_ws on the bot, and they get sourced automatically on the robot's startup. `bringup.launch.py` also gets launched automatically. We have also included both the Orbbec and sllidar packages there. In your new package, include a copy of the `rosbot` (or similar) packages from previous labs in the `src` folder, including your launch files in `a9_ws_lab3/rosbot/launch`. Place all configuration files (rviz, sensor_params, etc.) in `a9_ws_lab3/rosbot/config`. Be sure these are both added to the `share` directory in the `setup.py` file, as you did in the first lab. Copy the base `rosbot_arm` and `rosbot_msgs` packages from `lab3_ws/src/` in this repository into `a9_ws_lab3/src/` on the robot. *Also, be sure that you get any files from labs 1, 2 off of your prior robots, as we will be removing old workspaces after the first week of Lab 3*

   **Prepare your team**: Talk through how collaboration will work on this lab. You've worked on two labs to this point. What worked well for collaboration in the past? What didn't work well? How will you share files? How will you divide tasks? If you need to come in outside of lab hours, what days/times work well?

1. **Explore direct control of the rosbot arm**: We have provided a node in `rosbot_arm` called `arm_test`, that can be used to explore control of the arm directly. By setting `main(mode='direct')`, you can edit the list of (id, pulse) pairs called `targets` that is provided in the file, to test the effect of each joint. The joints of the arm are given ids=1-5, while the gripper is given id=10. For these servos, a timed pulse between 0 and 1000 ms corresponds to an angle from -120 to 120 degrees, and commands are sent as pulses. The only limits you need to pay close attention to are on joint 2. **Keep the pulse width between 125 and 775 for joint 2**, to protect the screen and the arm. Note that in `arm_test`, commands are sent to the on-board STM microcontroller using the `Board` class defined in the `ros_robot_controller_sdk` node. When you write your own arm_control node later, you can reference this node. To send commands to the arm, you can use the function `bus_servo_set_position(duration, targets)`, and you can read positions with `bus_servo_read_position(id)`. For now, just change the variables in `targets` and see what the robot does!
2. **Write your own ROS2 messages and service**: Next, come up with a plan as a team for how you'd like to send messages about the arm between the `arm_control` and `IK_node` nodes: its forward positions, gripper control, and target positions for inverse kinematics. You'll choose your own topic names and write your own message types for these. Message types are surprisingly straightforward to write. Use [this tutorial](https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html) to help you get started. You can use the `rosbot_msgs` template, but you will need to update the `CMakeLists.txt` file with your own message types. Also, create a service type for the robot for the service described in the next step.
3. **Write the backend arm_control node**: Write a node that takes your custom forward command ROS messages and sends those commands to the arm. This node should also include a service, as described in [this tutorial](https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html), to send current angle information from the board. To test this `arm_control` node, you can use the `arm_test` forward mode, although you will need to do a bit of work to configure the publisher to your message type.
4. **Write the inverse kinematics node**: Work out the inverse kinematics of your arm, given its end-effector xyz location and local roll/pitch. For our pick and place goals, the local pitch angle is -90 degrees, while the roll angle will be whatever it needs to be to grasp the block. Test your inverse kinematics node on some example configurations to be sure that it works as expected. Test whether your inverse kinematics returns realistic angles and send a warning if the request is not okay. You can send a warning message type with `get_logger().warn('message')`. The logger has five priority levels (of increasing severity): `debug`, `info`, `warn`, `error`, and `fatal`.
5. **Use the provided block detector**: The professor's [block_detector package](https://github.com/gknave/megn441/tree/lab3/lab3_ws/src/block_detector) is included in `src/block_detector`. Its `BlockDetection.msg` is included in `rosbot_msgs` and registered in `CMakeLists.txt`. The detector publishes one `rosbot_msgs/msg/BlockDetection` per detected block on `/block_detector/block_detections`, containing `header`, `color`, and `position` (x, y, z in meters). The position is in the camera frame named by `header.frame_id`. Your sequencer must transform it to `base_footprint` before sending an IK target.

   **Build on the robot**, from this workspace (using zsh):

   ```zsh
   cd ~/b1l3_ws
   source /opt/ros/humble/setup.zsh
   sudo apt update
   sudo apt install python3-opencv python3-numpy ros-humble-cv-bridge ros-humble-message-filters ros-humble-rqt-image-view
   colcon build --symlink-install --packages-select rosbot_msgs rosbot_arm block_detector
   source install/setup.zsh
   ```

   **Run with the robot's desktop/display available**:

   ```zsh
   ros2 launch block_detector detector_launch.py
   ```

   This starts the camera as `depth_cam` with depth registration enabled, the detector, and an image viewer. Select `/block_detector/debug_image` in the viewer. Run only one camera driver; stop any existing camera launch before using this combined launch.

   **Over SSH without a display**, start the camera in one terminal and the detector in another. Source `~/b1l3_ws/install/setup.zsh` in each terminal first:

   ```zsh
   # Terminal 1 (skip if this registered camera is already running)
   ros2 launch orbbec_camera dabai_dcw.launch.py camera_name:=depth_cam depth_registration:=true align_mode:=HW
   ```

   ```zsh
   # Terminal 2
   ros2 run block_detector block_detector
   ```

   To see detections in another sourced terminal:

   ```zsh
   ros2 topic echo /block_detector/block_detections
   ```

   The detector needs `/depth_cam/color/image_raw`, `/depth_cam/depth/image_raw`, and `/depth_cam/color/camera_info`; depth must be aligned to color. The sample bag/image paths in the package's original README are examples from its author's computer, not files included here. Detection can be tested when the robot is available.

   Imported from upstream revision [`318e309`](https://github.com/gknave/megn441/commit/318e309d4d058ab79f53852bc780a41dfabbc1a0). The detector code is unchanged; missing dependency declarations were added to its `package.xml`.

6. **Write a final sequencer node to tell the robot how to stack the blocks**: I recommend putting this node in your `rosbot` or `rosbot_arm` package, but you can of course create a new package if you prefer. You will need to modify your `setup.py` to tell it about your new node. In this node, you'll send requests and messages to the other nodes to identify the block locations, pick them up, and place them in-line with the robot arm base `20 cm` to the right of the robot on the ground. Stack the blocks on top of one-another with red on the bottom, then green, then blue.

   To transform the point into the `base_footprint` frame, you'll need to use a TF2 Buffer. There is [documentation here](https://docs.ros.org/en/humble/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Py.html) that is a bit hard to follow. The relevant parts are creating a TF Buffer. A TF Buffer listens to the published transforms. Use `tf_buffer.lookup_transform` with target frame `base_footprint` and source frame `detection.header.frame_id`, then use the function below to build the transformation matrix. Do not assume the source frame is named `depth_cam`; use the frame reported by the detector. Note that using numpy, you can use the `@` for matrix multiplication. I use quaternions below because the rotation outputs in quaternions.

   ```python
   def quat_to_T(q, t):
    """Convert a quaternion (x, y, z, w) and translation (x, y, z) to a 4x4 transformation matrix."""
    n = np.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
    qx, qy, qz, qw = q.x/n, q.y/n, q.z/n, q.w/n
    return np.array([
        [1 - 2*(qy*qy + qz*qz), 2*(qx*qy - qz*qw),     2*(qx*qz + qy*qw), t.x],
        [2*(qx*qy + qz*qw),     1 - 2*(qx*qx + qz*qz), 2*(qy*qz - qx*qw), t.y],
        [2*(qx*qz - qy*qw),     2*(qy*qz + qx*qw),     1 - 2*(qx*qx + qy*qy), t.z],
        [0, 0, 0, 1]
    ])
   ```

   I would recommend sending your arm to a set forward and down-facing configuration, identifying blocks, and then moving through several pre-defined poses on its way to the target. If you're dropping the block, try slowing down.

## Lab Grading

The grading of each lab is based 50\% on the successful completion of the lab. For this lab, that 50\% breaks down into:

- 10\% - Write your own messages/services
- 15\% - Demonstrate topic-based control of the arm
- 20\% - Demonstrate correct inverse kinematics of the arm
- 5\% - Stack blocks with the arm from pre-programmed positions OR autonomously move the gripper to the block at any position
- **10\% Extra Credit** - Demonstrate autonomous pick and place of the two or more blocks into a stack.

### Lab Report Guidelines

The guidelines below will be used in grading your lab report. Be sure to include everything that the guidelines below mention for full credit!

#### 1. Problem Statement

- Write a succinct 1-3 sentence description of the goals of this lab.

#### 2. Methods

- Describe your team's contributions to the software of the robot for Lab 3
- Describe the new messages/services that you have written
- Describe the key equations used to calculate the inverse kinematics of the arm.
- Explain what a TF buffer does.

#### 3. Results

- Describe how the RGBD camera represents its data.
- Include a video of your robot demonstrating the lab grading goals. A video of autonomous pick and place should demonstrate all of the other pieces, and if you don't quite make it there, then you can demonstrate as many of the other parts as possible.
- Explain how your robot's arm control works: detailing which messages are sent to which nodes, and what values are being sent.

#### 4. Conclusions

- Discuss what your team's biggest lessons learned are from this lab.
- What did your robot do well?
- What could you do to improve your robot's pick and place abilities, given more time?
- Discuss the challenges, if any, that your team had writing the arm control for this lab.

#### AI Appendix

- Include a 1 paragraph reflection on the questions below, whether or not you used AI.
  - Did you use any AI to support support the completion of this lab? Why or why not?
  - If no, how could it have helped? What did you gain by avoiding AI use?
  - If yes, how was your experience of using it? How did it help? What did you miss out on by using AI?
  - If you used AI, what resources do you think it used in generating its answers?
  - If you used AI, please copy and paste your interactions below:

#### Others

- Be sure to upload your code as a Zip file or a link to a github page (please don't zip build, install, log).
- If including a link to a video, make sure that it works from a private browser (so the TAs don't have to log in or have access to it)
