import cv2

def bitwise_xor(input_filepath_1: str, input_filepath_2: str, output_filepath: str):
    try:
        img1 = cv2.imread(input_filepath_1)
        img2 = cv2.imread(input_filepath_2)

        diff = cv2.bitwise_xor(img1, img2)
        cv2.imwrite(output_filepath, diff)
        return True
    except Exception as e:
        print(f"Error while doing a bitwise xor: {e}")
        return False

def create_rectangle(input_filepath: str, output_filepath: str, top_left_point: tuple, bottom_right_point: tuple):
    try:
        image = cv2.imread(input_filepath)
        cv2.rectangle(image, top_left_point, bottom_right_point, (0, 0, 255), 2)
        cv2.imwrite(output_filepath, image)
        return True
    except Exception as e:
        print(f"Error while creating a rectangle: {e}")
        return False