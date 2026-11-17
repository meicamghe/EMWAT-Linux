# Building and testing the EMWAT Linux components

This repository currently contains a Python local-bridge foundation, a LibreOffice UNO adapter, and a partially implemented native C++ image/scanner core. A green component test suite is not an end-to-end Almas Gam compatibility claim.

## Native image/scanner core

Ubuntu/Debian build dependencies:

```bash
sudo apt update
sudo apt install -y build-essential cmake pkg-config \
  libpng-dev libjpeg-dev libtiff-dev libsane-dev
```

Configure, build and run the native tests:

```bash
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build --parallel
ctest --test-dir native/build --output-on-failure
```

The native tests cover pixel transforms, image codecs, multi-page TIFF/document I/O, transactional load/save behavior, scanner interface contracts, and scanner-to-document batch handling. Physical scanner hardware is not required by the current unit tests.

## Python bridge

```bash
cd python
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
PYTHONPATH=src python -m unittest discover -s tests -v
```

The Python suite covers the local HTTP/XML bridge, EditWordDocument request parsing, Word field decoding, Writer metadata inventory, and payload inventory.

## LibreOffice UNO integration

Install LibreOffice Writer and the distro's Python UNO binding (commonly `libreoffice-writer` and `python3-uno`). The integration suite is optional in the ordinary Python run. To opt in, use the system Python that can import `uno` and run:

```bash
EMWAT_RUN_LIBREOFFICE_INTEGRATION=1 PYTHONPATH=src \
  python -m unittest discover -s tests -p 'test_libreoffice*.py' -v
```

## Important compatibility boundaries

- The actual Almas template and a safe real request/response capture are still needed to verify the 180-field mapping and image/signature placement.
- LibreOffice custom-property metadata order has not been proven equivalent to Word COM enumeration order.
- `signData` framing and external `paramId` resolution remain unverified.
- SANE scanning is implemented against the API contract but has not yet been validated on physical scanner hardware.
- Do not expose this bridge to non-loopback interfaces or production traffic until the complete authentication/origin and response contracts are verified.


## EditWord payload limits

The LibreOffice composition factory defaults to a 64 MiB decoded Word document limit, a 128 MiB HTTP request limit, and a 96 MiB HTTP response limit. These are bounded defaults that allow for Base64 expansion and the XML envelope. Deployments can lower or raise the limits explicitly; keep the HTTP request cap large enough for the encoded document plus configuration and other parameters.
