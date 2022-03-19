import argparse

from src.face import FaceWorker


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-et', '--state-expiration-time', type=int, default=120, help='Seconds')
    parser.add_argument('-tt', '--tired-time', type=int, default=25, help='Minutes')
    args = parser.parse_args()
    FaceWorker(
        image_file='pic/user_photo.jpg',
        vflip=True
    ).run(
        state_expiration_time=args.state_expiration_time,
        tired_time=args.tired_time,
        display_vflip=True,
        display_hflip=False
    )
