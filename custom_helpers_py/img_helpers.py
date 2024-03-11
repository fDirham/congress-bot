import numpy


def convert_pil_to_opencv_img(pil_image):
    open_cv_image = numpy.array(pil_image)
    return open_cv_image[:, :, ::-1].copy()
