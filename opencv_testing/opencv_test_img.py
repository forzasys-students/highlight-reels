import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

input_image_path = 'opencv_testing/16_9_image.jpg'  # Change this to the path of your input image
output_image_path = 'opencv_testing/image_with_graphics.jpg'  # Output image path

image = cv2.imread(input_image_path)
if image is None:
    print('Error opening image')
    exit()

# Convert BGR image to RGBA format (PIL uses RGBA)
image_rgba = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)
pil_image = Image.fromarray(image_rgba)

# Define graphics parameters
msg_font_size = 25
overlay_position_y_offset = 0.92
overlay_position_x_offset = 0.05

# Create a drawing object
draw = ImageDraw.Draw(pil_image)

# Draw graphics on the image
draw.rectangle([(50, 50), (200, 200)], outline=(255, 0, 0), width=3)  # Example rectangle

# Convert back to BGR format for OpenCV
image_with_graphics = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGR)

# Save the image with graphics
cv2.imwrite(output_image_path, image_with_graphics)
print(f"Image with graphics saved at '{output_image_path}'")