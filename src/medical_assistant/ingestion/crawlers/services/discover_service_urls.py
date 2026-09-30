"""Discover public Vinmec Online service URLs from the sitemap and listing."""

from .service_crawler import main

if __name__ == "__main__":
    raise SystemExit(main(["--discover"]))
