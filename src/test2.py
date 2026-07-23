import cv2

# Load the two images (ensure they are identical in size)
img1 = cv2.imread('slices/z0_0.5.png')
img2 = cv2.imread('slices/z0_0.png')

# Perform bitwise XOR operation
# Identical pixels will become 0 (black), different pixels will stand out
diff = cv2.bitwise_xor(img1, img2)

# Display the resulting difference image
cv2.imshow('Differences Revealed', diff)

# Keep the window open until a key is pressed
cv2.waitKey(0)
cv2.destroyAllWindows()

# Optional: Save the output image
cv2.imwrite('xor_difference.png', diff)