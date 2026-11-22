"""Entry point for Gemini Catgirl Desktop Pet."""
import sys

from catgirl_pet import app, monitor


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if '--monitor' in args:
        return monitor.main()
    return app.main()


if __name__ == '__main__':
    sys.exit(main())
