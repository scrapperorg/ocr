from api.utils.file_util import secure_filename


def test_secure_filename():
    # Test ASCII filenames
    assert secure_filename('test.pdf') == 'test.pdf'
    assert secure_filename('test 123.pdf') == 'test_123.pdf'
    assert secure_filename('test/123.pdf') == 'test_123.pdf'
    assert secure_filename('test|123.pdf') == 'test123.pdf'

    # Test unicode filenames
    assert secure_filename('测试.pdf') != '测试.pdf'
    assert secure_filename('测试 123.pdf') == '123.pdf'
    assert secure_filename('测试/123.pdf') == '123.pdf'
    assert secure_filename('测试|123.pdf') == '123.pdf'
    assert secure_filename('șțîăâ.pdf') == 'stiaa.pdf'
    assert secure_filename('șțîăâ.pdf') == 'stiaa.pdf'

    # Test empty filenames
    assert secure_filename('') != ''
    assert secure_filename(' ') != ''
    assert secure_filename('   .pdf') != ''
