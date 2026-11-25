/*
 * Experimental Wine-only probe for the internal EmwatMethods Base64 decoder.
 * It maps the BPL with DONT_RESOLVE_DLL_REFERENCES, so Delphi package
 * initialization and imports are not executed. This is not production code.
 *
 * Build with i686-w64-mingw32-gcc and run under Wine 11 in a disposable
 * WINEPREFIX. Verify the BPL SHA-256 before running; see
 * docs/WORD-FIELD-VALUE-DECODING.md.
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

typedef unsigned char (__attribute__((cdecl, regparm(3))) *DecodeFn)(
    const unsigned char **input,
    unsigned int length,
    unsigned char **output);

typedef struct {
    const char *name;
    const char *encoded;
    unsigned char expected_success;
    unsigned char expected_prefix[3];
    unsigned int expected_prefix_length;
    int expect_unwritten_output;
} DecodeCase;

static const DecodeCase cases[] = {
    {"three_bytes", "TWFu", 1, {0x4d, 0x61, 0x6e}, 3, 0},
    {"one_byte_padding", "QQ==", 1, {0x41, 0, 0}, 1, 0},
    {"two_byte_padding", "QUI=", 1, {0x41, 0x42, 0}, 2, 0},
    /* The decoder writes A before rejecting the third character. */
    {"invalid_alphabet", "QQ?=", 0, {0x41, 0, 0}, 1, 0},
    {"invalid_length", "TWE", 0, {0, 0, 0}, 0, 1},
    /* The raw decoder stops at the third-character '=' and ignores the last. */
    {"noncanonical_padding", "QQ=A", 1, {0x41, 0, 0}, 1, 0},
};

static int run_case(DecodeFn decode, const DecodeCase *test_case) {
    unsigned char output[32];
    const unsigned char *input_pointer =
        (const unsigned char *)test_case->encoded;
    unsigned char *output_pointer = output;
    unsigned char success;
    unsigned int index;

    memset(output, 0xa5, sizeof(output));
    success = decode(&input_pointer,
                     (unsigned int)strlen(test_case->encoded),
                     &output_pointer);
    if (success != test_case->expected_success) {
        fprintf(stderr, "%s: unexpected success result %u\n",
                test_case->name, (unsigned int)success);
        return 0;
    }
    if (test_case->expect_unwritten_output) {
        if (output[0] != 0xa5) {
            fprintf(stderr, "%s: output changed before length rejection\n",
                    test_case->name);
            return 0;
        }
    } else {
        for (index = 0; index < test_case->expected_prefix_length; ++index) {
            if (output[index] != test_case->expected_prefix[index]) {
                fprintf(stderr, "%s: output byte %u was %02x\n",
                        test_case->name, index, output[index]);
                return 0;
            }
        }
    }

    printf("%s success=%u output=", test_case->name, (unsigned int)success);
    for (index = 0; index < test_case->expected_prefix_length; ++index)
        printf("%02x", output[index]);
    if (test_case->expect_unwritten_output)
        printf("(unwritten)");
    putchar('\n');
    return 1;
}

int main(int argc, char **argv) {
    HMODULE module;
    DecodeFn decode;
    unsigned int index;
    int all_passed = 1;

    if (argc != 2) {
        fprintf(stderr, "usage: %s /path/to/EmwatMethods.bpl\n", argv[0]);
        return 2;
    }
    module = LoadLibraryExA(argv[1], NULL, DONT_RESOLVE_DLL_REFERENCES);
    if (module == NULL) {
        fprintf(stderr, "LoadLibraryEx failed: %lu\n",
                (unsigned long)GetLastError());
        return 3;
    }

    /* RVA 0x73700 is decoder VA 0x00473700 at preferred base 0x00400000. */
    decode = (DecodeFn)((unsigned char *)module + 0x73700);
    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index)
        all_passed &= run_case(decode, &cases[index]);

    FreeLibrary(module);
    return all_passed ? 0 : 1;
}
