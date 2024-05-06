import cv2
import os
import numpy as np

font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1.681818
text_size, _ = cv2.getTextSize("ALLSVENSKAN", font, font_scale, 2)
print(text_size)