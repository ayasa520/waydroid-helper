def float_to_u16fp(f: float):
    assert f >= 0.0 and f <= 1.0
    u = int(f * (2**16))
    if u >= 0xFFFF:
        assert u == 0x10000
        u = 0xFFFF
    return u


def float_to_i16fp(f: float):
    assert f >= -1.0 and f <= 1.0
    i = int(f * (2**15))
    assert i >= -0x8000
    if i >= 0x7FFF:
        assert i == 0x8000
        i = 0x7FFF

    return i