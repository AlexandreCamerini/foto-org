import sys

if len(sys.argv) > 1:
    from fotoorganizer.cli import main
else:
    from fotoorganizer.app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
