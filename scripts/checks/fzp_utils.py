import os

class FZPUtils:
    @staticmethod
    def get_svg_path(fzp_path, image):
        dir_path = os.path.dirname(fzp_path)
        up_one_level = os.path.dirname(dir_path)
        return os.path.join(up_one_level, 'svg', 'core', image)
