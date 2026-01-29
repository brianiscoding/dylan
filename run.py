from client import client
import config as config


def main():
    client(config.host, config.port, config.scheme, config.silent)


if __name__ == "__main__":
    main()
