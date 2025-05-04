# Edge Impulse - OpenMV FOMO Object Detection Example with Serial Communication
#
# This work is licensed under the MIT license.
# Copyright (c) 2013-2024 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
import sensor
import time
import ml
from ml.utils import NMS
import math
import image
import pyb  # For UART communication

# Set up UART for communication (using configuration from nicla_main.py)
uart = pyb.UART(1, 115200)
uart.init(115200, bits=8, parity=None, stop=1)

# Configure LED for visual feedback
led = pyb.LED(1)  # Usually red LED
led2 = pyb.LED(3) if hasattr(pyb.LED, '3') else None  # Green LED if available

sensor.reset()  # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565)  # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA)  # Set frame size to QVGA (320x240)
sensor.skip_frames(time=2000)  # Let the camera adjust.

# Default parameters (can be modified via commands from PC)
min_confidence = 0.6
delay_ms = 1000
is_running = True

threshold_list = [(math.ceil(min_confidence * 255), 255)]

# Load built-in model
model = ml.Model("trained")
print(model)

colors = [  # Add more colors if you are detecting more than 7 types of classes at once.
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
]

# Define distance thresholds for each class
class_distance_thresholds = {
    # Format: 'class_name': threshold_in_pixels
    'Unibic': 80,
    'KitKat': 40,
    'goodday': 80,
    'HidenSeek': 80,
    'bird': 20,
}

# Default threshold to use when a class is not in the dictionary
DEFAULT_DISTANCE_THRESHOLD = 30

# FOMO outputs an image per class where each pixel in the image is the centroid of the trained
# object. So, we will get those output images and then run find_blobs() on them to extract the
# centroids. We will also run get_stats() on the detected blobs to determine their score.
def fomo_post_process(model, inputs, outputs):
    n, oh, ow, oc = model.output_shape[0]
    # Create NMS without custom parameters as they're not supported in this version
    nms = NMS(ow, oh, inputs[0].roi)

    for i in range(oc):
        img = image.Image(outputs[0][0, :, :, i] * 255)
        blobs = img.find_blobs(
            threshold_list, x_stride=1, area_threshold=1, pixels_threshold=1, merge=True
        )

        for b in blobs:
            rect = b.rect()
            x, y, w, h = rect
            score = (
                img.get_statistics(thresholds=threshold_list, roi=rect).l_mean() / 255.0
            )
            nms.add_bounding_box(x, y, x + w, y + h, score, i)

    return nms.get_bounding_boxes()

def merge_nearby_detections(detection_list, label):
    """
    Merge nearby detections of the same class based on distance between centers.

    Args:
        detection_list: List of detections in format [((x,y,w,h), score), ...]
        label: The class label string to determine appropriate distance threshold

    Returns:
        List of merged detections
    """
    if not detection_list:
        return []

    # Get the appropriate distance threshold for this class
    distance_threshold = class_distance_thresholds.get(label, DEFAULT_DISTANCE_THRESHOLD)

    # Sort detections by score (highest first)
    detection_list.sort(key=lambda x: x[1], reverse=True)

    merged_detections = []
    used_indices = set()

    for i, ((x1, y1, w1, h1), score1) in enumerate(detection_list):
        if i in used_indices:
            continue

        center_x1 = x1 + w1//2
        center_y1 = y1 + h1//2
        current_rect = (x1, y1, w1, h1)
        current_score = score1
        merged_count = 1

        # Find all nearby detections
        for j, ((x2, y2, w2, h2), score2) in enumerate(detection_list):
            if j == i or j in used_indices:
                continue

            center_x2 = x2 + w2//2
            center_y2 = y2 + h2//2

            # Calculate distance between centers
            distance = math.sqrt((center_x1 - center_x2)**2 + (center_y1 - center_y2)**2)

            # If close enough, merge them
            if distance < distance_threshold:
                used_indices.add(j)
                merged_count += 1

        # Only add if not merged with others (or it's the primary one)
        if merged_count <= 1 or i not in used_indices:
            merged_detections.append((current_rect, current_score))

    return merged_detections

# Function to process serial commands from the PC
def process_commands():
    if uart.any():
        cmd = uart.readline().decode('utf-8').strip()
        global min_confidence, delay_ms, is_running, threshold_list

        if cmd == "start":
            is_running = True
            uart.write("Detection started\r\n".encode('utf-8'))
        elif cmd == "stop":
            is_running = False
            uart.write("Detection stopped\r\n".encode('utf-8'))
        elif cmd.startswith("conf="):
            try:
                min_confidence = float(cmd.split("=")[1])
                threshold_list = [(math.ceil(min_confidence * 255), 255)]
                uart.write(f"Confidence set to {min_confidence}\r\n".encode('utf-8'))
            except:
                uart.write("Invalid confidence value\r\n".encode('utf-8'))
        elif cmd.startswith("delay="):
            try:
                delay_ms = int(cmd.split("=")[1])
                uart.write(f"Delay set to {delay_ms}ms\r\n".encode('utf-8'))
            except:
                uart.write("Invalid delay value\r\n".encode('utf-8'))
        elif cmd == "status":
            status = "Running" if is_running else "Stopped"
            uart.write(f"Status: {status}, Confidence: {min_confidence}, Delay: {delay_ms}ms\r\n".encode('utf-8'))
        else:
            uart.write(f"Unknown command: {cmd}\r\n".encode('utf-8'))

# New function to send detections in the format from nicla_main.py
def send_detection_nicla_format(detections_by_class):
    if not detections_by_class:
        return

    # Start building the detection message
    message = "DETECTION"

    # For each class and its detections
    for class_label, detections in detections_by_class.items():
        # Use the highest confidence detection for this class
        if not detections:
            continue

        # Sort by confidence (highest first)
        detections.sort(key=lambda x: x[1], reverse=True)
        highest_conf_detection = detections[0]
        _, score = highest_conf_detection

        # Add the item with format: |ItemName:Quantity:Confidence
        quantity = len(detections)  # Use the count of detections as quantity
        message += f"|{class_label}:{quantity}:{score:.2f}"

    # Send the message
    uart.write(f"{message}\r\n".encode('utf-8'))
    print(f"Sent: {message}")

# Function to print detection summary to terminal
def print_detection_summary(detections_by_class):
    if not detections_by_class:
        print("No objects detected")
        return

    print("\n----- DETECTION SUMMARY -----")

    # Count detections per class and track highest confidence
    for class_label, detections in detections_by_class.items():
        count = len(detections)
        highest_confidence = max([score for (_, score) in detections]) if detections else 0

        print(f"Object: {class_label}")
        print(f"  Quantity: {count}")
        print(f"  Confidence: {highest_confidence:.4f} ({int(highest_confidence * 100)}%)")

    print("----------------------------\n")

# Blink LED pattern to indicate script has started
for i in range(3):
    led.toggle()
    time.sleep(0.2)
    if led2:
        led2.toggle()
        time.sleep(0.2)

# Indicate ready
if led2:
    led2.on()

clock = time.clock()
uart.write("Object detection system ready\r\n".encode('utf-8'))
print("Object detection system ready")

while True:
    # Process any incoming commands
    process_commands()

    # Skip detection if not running
    if not is_running:
        time.sleep_ms(100)  # Small delay to prevent high CPU usage when idle
        continue

    # Flash LED for detection activity
    led.on()

    clock.tick()
    img = sensor.snapshot()

    # Start measuring processing time for object detection
    start_time = time.ticks_ms()

    # Create a dictionary to store detections by class
    all_detections = {}

    for i, detection_list in enumerate(model.predict([img], callback=fomo_post_process)):
        if i == 0:
            continue  # background class
        if len(detection_list) == 0:
            continue  # no detections for this class?

        class_label = model.labels[i]

        # Apply our custom merging with class-specific threshold
        filtered_detections = merge_nearby_detections(detection_list, class_label)
        all_detections[class_label] = filtered_detections

        # Draw the detections on the image (keep your existing drawing code)
        for (x, y, w, h), score in filtered_detections:
            center_x = math.floor(x + (w / 2))
            center_y = math.floor(y + (h / 2))

            # Draw a square instead of circle
            square_size = 24
            img.draw_rectangle(
                (center_x - square_size // 2, center_y - square_size // 2, square_size, square_size),
                color=colors[i],
                thickness=2
            )

            # Draw class name
            img.draw_string(center_x - 20, center_y - 30, class_label, color=colors[i], scale=1.5)

    # End measuring processing time
    end_time = time.ticks_ms()
    processing_time = time.ticks_diff(end_time, start_time)

    # Print detection summary to terminal
    print_detection_summary(all_detections)

    # Print the processing latency
    print("Detection latency: {} ms".format(processing_time))

    # Send detections in the nicla_main.py format
    send_detection_nicla_format(all_detections)

    # Send the latency over UART
    uart.write(f"LATENCY:{processing_time}ms\r\n".encode('utf-8'))

    # Also print FPS to terminal
    print("{} fps".format(clock.fps()))

    # Visual feedback based on number of detections
    num_detected = sum(len(detections) for detections in all_detections.values())
    for i in range(num_detected):
        led.toggle()
        time.sleep(0.1)

    led.off()

    # Wait according to the configured delay
    time.sleep_ms(delay_ms)
