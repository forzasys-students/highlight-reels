
import cv2
import numpy as np
import math

# Create a black image (all zeros)
image = 255 * np.ones((500, 500, 3), dtype=np.uint8)

# Define circle parameters
CENTER = (100, 100)

cv2.circle(image, CENTER, 96, (127,0,127), -1)

font = cv2.FONT_HERSHEY_SIMPLEX
TEXT_SCALE = 1.5
TEXT_THICKNESS = 2
text = "Hello Joseph!!"
text_size = cv2.getTextSize(text, font, 1, 2)[0]

TEXT_FACE = cv2.FONT_HERSHEY_DUPLEX
TEXT_SCALE = 1.5
TEXT_THICKNESS = 2
TEXT = "test"

text_size, _ = cv2.getTextSize(TEXT, TEXT_FACE, TEXT_SCALE, TEXT_THICKNESS)
text_origin = (int(CENTER[0] - text_size[0] / 2), int(CENTER[1] + text_size[1] / 2))

cv2.putText(image, TEXT, (text_origin[0], text_origin[1]), TEXT_FACE, TEXT_SCALE, (127,255,127), TEXT_THICKNESS, cv2.LINE_AA)

# Save the image
cv2.imwrite("circle_image.jpg", image)

print("Image saved as 'circle_image.jpg'")