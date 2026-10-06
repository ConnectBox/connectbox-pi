# Create Image (The Well)

This page used to hold a short 2021 procedure for making a Raspberry Pi image for
The Well.  Its steps (Raspbian Buster, the `pi`/`raspberry` login, copying the
card with `dd`) are out of date.

**Follow [making_an_image.md](making_an_image.md) instead.**  For a The Well image,
add these options to the build command in its step 3:

```
-e connectbox_default_hostname=TheWell -e lcd_logo=lcdwell_logo.png
```

(`make_cb.py` in connectbox-tools does the same when you answer "y" to "Do you
want to build TheWell?").  After testing, the image's WiFi network is named after
The Well.

## Relay Trust base images

Base images for The Well are stored in AWS S3 at
https://s3.console.aws.amazon.com/s3/buckets/thewellimages?region=us-west-2&tab=objects
and are available to download at https://chat.thewellcloud.cloud/chathost/images.html
