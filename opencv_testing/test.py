import cv2
import os
import numpy as np
from PIL import ImageColor

text_size = cv2.getTextSize(max(text, key=len), font_style, ((bottom_right[1]-top_left[1])*font_scale)/22, 2)