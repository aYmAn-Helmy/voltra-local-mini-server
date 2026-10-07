# Android production signing

Voltra Mobile uses the permanent package ID:

```text
com.ayman.voltra.voltra_mobile
```

Do not change this ID after production deployment.

The GitHub Actions workflow supports two signing modes:

1. **Production signing** when all four repository secrets below exist.
2. **Test/debug signing** when they are absent, so normal CI keeps working.

Required GitHub repository secrets:

- `VOLTRA_ANDROID_KEYSTORE_B64`
- `VOLTRA_ANDROID_KEYSTORE_PASSWORD`
- `VOLTRA_ANDROID_KEY_ALIAS`
- `VOLTRA_ANDROID_KEY_PASSWORD`

Encode the keystore on Linux/macOS:

```bash
base64 -w0 voltra-release.jks
```

On macOS, if `-w0` is unavailable:

```bash
base64 < voltra-release.jks | tr -d '\n'
```

Store the keystore and its passwords in at least two secure offline locations. If this
key is lost, Android will not accept future updates signed by a different key for the
same package ID.

The first switch from the original v1.0 test build to the production key can require
uninstalling the old test build once. After the production-signed build is installed,
future versions signed with the same key update normally.
