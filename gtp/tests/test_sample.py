from gtp.src.main import GTPBlock
import pytest
from lark.exceptions import VisitError

from gtp.src.parsers import OperationError

class GTPTester:

    def setup_method(self):
        self.scopes = [dict()]
        self.readonlies = set()
        self.outputs : list[str] = []

    def run_gtp_block(self, contents: str):
        return GTPBlock(self.scopes, self.readonlies, self.outputs, 0, 0, contents).run()


@pytest.mark.dependency(name='TestSet')
class TestSet(GTPTester):

    @pytest.mark.dependency(name='set_int_pos')
    def test_int_pos(self):
        self.run_gtp_block("x = 5;")
        assert self.scopes[0]['x'] == 5

    def test_int_neg(self):
        self.run_gtp_block("x = -5;")
        assert self.scopes[0]['x'] == -5

    def test_str_single(self):
        self.run_gtp_block("x = 'foo';")
        assert self.scopes[0]['x'] == 'foo'

    def test_str_double(self):
        self.run_gtp_block('x = "bar";')
        assert self.scopes[0]['x'] == 'bar'

    @pytest.mark.dependency(name='set_true')
    def test_true(self):
        self.run_gtp_block('x = true;')
        assert self.scopes[0]['x'] == True

    @pytest.mark.dependency(name='set_false')
    def test_false(self):
        self.run_gtp_block('x = false;')
        assert self.scopes[0]['x'] == False

    def test_null(self):
        self.run_gtp_block('x = null;')
        assert self.scopes[0]['x'] is None

    def test_fstring(self):
        self.run_gtp_block('x = f"Matchbox {20}\\ {\'is a band\'}";')
        assert self.scopes[0]['x'] == 'Matchbox 20 is a band'

    @pytest.mark.dependency(name='set_array')
    def test_array(self):
        self.run_gtp_block('x = {1, "two", false, true, null};')
        for a, b in zip(self.scopes[0]['x'], (1, "two", False, True, None)):
            assert a == b

    def test_nested_array(self):
        self.run_gtp_block('x = {1, "two", {"red", "blue"}, null};')
        for a, b in zip(self.scopes[0]['x'], (1, "two", ["red", "blue"], None)):
            if type(a) == list:
                for c, d in zip(a, b):
                    assert c == d
            else:
                assert a == b

    @pytest.mark.dependency(depends=['set_array'])
    def test_indexer(self):
        self.run_gtp_block('x = {1, 2, 3}; x[2] = 4;')
        for a, b in zip(self.scopes[0]['x'], [1, 2, 4]):
            assert a == b

    def test_chained(self):
        self.run_gtp_block('x = y = 5;')
        assert self.scopes[0]['x'] == 5
        assert self.scopes[0]['y'] == 5

    def test_readonly(self):
        try:
            self.readonlies.add('x')
            self.run_gtp_block('x = 7;')
        except VisitError as e:
            if isinstance(e.orig_exc, OperationError):
                assert e.orig_exc.args[0] == "Cannot assign value to symbol 'x': it is readonly"
                return
        raise Exception("Expected to raise a VisitError with orig_exc of type ValueError")


class TestEcho(GTPTester):

    def test_int_pos(self):
        self.run_gtp_block("echo 5;")
        assert self.outputs[0].strip() == '5'

    def test_int_neg(self):
        self.run_gtp_block("echo -5;")
        assert self.outputs[0].strip() == '-5'

    def test_str_single(self):
        self.run_gtp_block("echo 'foo';")
        assert self.outputs[0].strip() == 'foo'

    def test_str_double(self):
        self.run_gtp_block('echo "bar";')
        assert self.outputs[0].strip() == 'bar'

    def test_true(self):
        self.run_gtp_block('echo true;')
        assert self.outputs[0].strip() == 'true'

    def test_false(self):
        self.run_gtp_block('echo false;')
        assert self.outputs[0].strip() == 'false'

    def test_null(self):
        self.run_gtp_block('echo null;')
        assert self.outputs[0].strip() == 'null'

    @pytest.mark.dependency(depends=["set_int_pos"])
    def test_var(self):
        self.run_gtp_block('x = 5; echo x;')
        assert self.outputs[0].strip() == '5'

    def test_fstring(self):
        self.run_gtp_block('echo f"Matchbox {20}\\ {\'is a band\'}";')
        assert self.outputs[0].strip() == 'Matchbox 20 is a band'

    def test_array(self):
        self.run_gtp_block('echo {1, "two", false, true, null};')
        assert self.outputs[0].strip() == '{1, "two", false, true, null}'

    def test_nested_array(self):
        self.run_gtp_block('echo {1, "two", {"red", "blue"}, null};')
        assert self.outputs[0].strip() == '{1, "two", {"red", "blue"}, null}'

    @pytest.mark.dependency(depends=['set_array', 'set_int_pos'])
    def test_indexer(self):
        self.run_gtp_block('x = {1, 2, 3}; echo x[2];')
        assert self.outputs[0].strip() == '3'


@pytest.mark.dependency(name='TestAnd', depends=['TestSet'])
class TestAnd(GTPTester):

    def test_false_false(self):
        self.run_gtp_block('x = false and false;')
        assert self.scopes[0]['x'] == False

    def test_false_true(self):
        self.run_gtp_block('x = false and true;')
        assert self.scopes[0]['x'] == False

    def test_true_false(self):
        self.run_gtp_block('x = true and false;')
        assert self.scopes[0]['x'] == False

    def test_true_true(self):
        self.run_gtp_block('x = true and true;')
        assert self.scopes[0]['x'] == True

    def test_var_false_false(self):
        self.run_gtp_block('y = false; x = y and y;')
        assert self.scopes[0]['x'] == False

    def test_var_false_true(self):
        self.run_gtp_block('y = false; z = true; x = y and z;')
        assert self.scopes[0]['x'] == False

    def test_var_true_false(self):
        self.run_gtp_block('y = false; z = true; x = z and y;')
        assert self.scopes[0]['x'] == False

    def test_var_true_true(self):
        self.run_gtp_block('y = true; x = y and y;')
        assert self.scopes[0]['x'] == True

    def test_true_zero(self):
        self.run_gtp_block('x = true and 0;')
        assert self.scopes[0]['x'] == 0

    def test_true_nonzero(self):
        self.run_gtp_block('x = true and 5;')
        assert self.scopes[0]['x'] == 5

    def test_true_str(self):
        self.run_gtp_block('x = true and "false";')
        assert self.scopes[0]['x'] == 'false'

    def test_true_null(self):
        self.run_gtp_block('x = true and null;')
        assert self.scopes[0]['x'] == None


@pytest.mark.dependency(name='TestOr', depends=['TestSet'])
class TestOr(GTPTester):

    def test_false_false(self):
        self.run_gtp_block('x = false or false;')
        assert self.scopes[0]['x'] == False

    def test_false_true(self):
        self.run_gtp_block('x = false or true;')
        assert self.scopes[0]['x'] == True

    def test_true_false(self):
        self.run_gtp_block('x = true or false;')
        assert self.scopes[0]['x'] == True

    def test_true_true(self):
        self.run_gtp_block('x = true or true;')
        assert self.scopes[0]['x'] == True

    def test_var_false_false(self):
        self.run_gtp_block('y = false; x = y or y;')
        assert self.scopes[0]['x'] == False

    def test_var_false_true(self):
        self.run_gtp_block('y = false; z = true; x = y or z;')
        assert self.scopes[0]['x'] == True

    def test_var_true_false(self):
        self.run_gtp_block('y = false; z = true; x = z or y;')
        assert self.scopes[0]['x'] == True

    def test_var_true_true(self):
        self.run_gtp_block('y = true; x = y or y;')
        assert self.scopes[0]['x'] == True

    def test_true_zero(self):
        self.run_gtp_block('x = true or 0;')
        assert self.scopes[0]['x'] == True

    def test_true_nonzero(self):
        self.run_gtp_block('x = true or 5;')
        assert self.scopes[0]['x'] == True

    def test_true_str(self):
        self.run_gtp_block('x = true or "false";')
        assert self.scopes[0]['x'] == True

    def test_true_null(self):
        self.run_gtp_block('x = true or null;')
        assert self.scopes[0]['x'] == True


@pytest.mark.dependency(depends=['TestAnd', 'TestOr'])
class TestFakeTernary(GTPTester):

    def test_false(self):
        self.run_gtp_block('x = false and 5 or "foo";')
        assert self.scopes[0]['x'] == "foo"

    def test_true(self):
        self.run_gtp_block('x = true and 5 or "foo";')
        assert self.scopes[0]['x'] == 5


@pytest.mark.dependency(name='TestAdd', depends=['TestSet'])
class TestAdd(GTPTester):

    def test_ints(self):
        self.run_gtp_block('x = 5 + 7;')
        assert self.scopes[0]['x'] == 12

    def test_strs(self):
        self.run_gtp_block('x = "foo" + "bar";')
        assert self.scopes[0]['x'] == 'foobar'

    def test_array_array(self):
        self.run_gtp_block('x = {1, 2, 3} + {4, 5, 6};')
        for a, b in zip(self.scopes[0]['x'], [1, 2, 3, 4, 5, 6]):
            assert a == b


@pytest.mark.dependency(depends=['TestAdd'])
class TestIAdd(GTPTester):

    def test_ints(self):
        self.run_gtp_block('x = 5; y = x += 7;')
        assert self.scopes[0]['x'] == 12
        assert self.scopes[0]['y'] == 12

    def test_strs(self):
        self.run_gtp_block('x = "foo"; y = x += "bar";')
        assert self.scopes[0]['x'] == 'foobar'
        assert self.scopes[0]['y'] == 'foobar'

    def test_array_array(self):
        self.run_gtp_block('x = {1, 2, 3}; y = x += {4, 5, 6};')
        for a, b, c in zip(self.scopes[0]['x'], self.scopes[0]['y'], [1, 2, 3, 4, 5, 6]):
            assert a == b and b == c


@pytest.mark.dependency(name='TestSub', depends=['TestSet'])
class TestSub(GTPTester):

    def test_ints(self):
        self.run_gtp_block('x = 5 - 7;')
        assert self.scopes[0]['x'] == -2


@pytest.mark.dependency(depends=['TestSub'])
class TestISub(GTPTester):

    def test_ints(self):
        self.run_gtp_block('x = 5; y = x -= 7;')
        assert self.scopes[0]['x'] == -2
        assert self.scopes[0]['y'] == -2


@pytest.mark.dependency(name='TestMul', depends=['TestSet'])
class TestMul(GTPTester):

    def test_ints(self):
        self.run_gtp_block('x = 5 * 7;')
        assert self.scopes[0]['x'] == 35

    def test_int_str(self):
        self.run_gtp_block('x = 5 * "ps";')
        assert self.scopes[0]['x'] == 'pspspspsps'

    def test_str_int(self):
        self.run_gtp_block('x = "sp" * 5;')
        assert self.scopes[0]['x'] == 'spspspspsp'


@pytest.mark.dependency(depends=['TestMul'])
class TestIMul(GTPTester):

    def test_ints(self):
        self.run_gtp_block('x = 5; y = x *= 7;')
        assert self.scopes[0]['x'] == 35
        assert self.scopes[0]['y'] == 35

    def test_int_str(self):
        self.run_gtp_block('x = 5; y = x *= "ps";')
        assert self.scopes[0]['x'] == 'pspspspsps'
        assert self.scopes[0]['y'] == 'pspspspsps'

    def test_str_int(self):
        self.run_gtp_block('x = "sp"; y = x *= 5;')
        assert self.scopes[0]['x'] == 'spspspspsp'
        assert self.scopes[0]['y'] == 'spspspspsp'


@pytest.mark.dependency(name='TestDiv', depends=['TestSet'])
class TestDiv(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 25 / 5;')
        assert self.scopes[0]['x'] == 5

    def test_ints_2(self):
        self.run_gtp_block('x = 24 / 5;')
        assert self.scopes[0]['x'] == 4

    def test_strs(self):
        self.run_gtp_block('x = "a,b,c,d,e" / ",";')
        for a, b in zip(self.scopes[0]['x'], ['a', 'b', 'c', 'd', 'e']):
            assert a == b


@pytest.mark.dependency(depends=['TestDiv'])
class TestIDiv(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 25; y = x /= 5;')
        assert self.scopes[0]['x'] == 5
        assert self.scopes[0]['y'] == 5

    def test_ints_2(self):
        self.run_gtp_block('x = 24; y = x /= 5;')
        assert self.scopes[0]['x'] == 4
        assert self.scopes[0]['y'] == 4

    def test_strs(self):
        self.run_gtp_block('x = "a,b,c,d,e"; y = x /= ",";')
        for a, b, c in zip(self.scopes[0]['x'], self.scopes[0]['y'], ['a', 'b', 'c', 'd', 'e']):
            assert a == b and b == c


@pytest.mark.dependency(name='TestMod', depends=['TestSet'])
class TestMod(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 25 % 5;')
        assert self.scopes[0]['x'] == 0

    def test_ints_2(self):
        self.run_gtp_block('x = 28 % 5;')
        assert self.scopes[0]['x'] == 3


@pytest.mark.dependency(depends=['TestMod'])
class TestIMod(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 25; y = x %= 5;')
        assert self.scopes[0]['x'] == 0
        assert self.scopes[0]['y'] == 0

    def test_ints_2(self):
        self.run_gtp_block('x = 28; y = x %= 5;')
        assert self.scopes[0]['x'] == 3
        assert self.scopes[0]['y'] == 3


@pytest.mark.dependency(name='TestPow', depends=['TestSet'])
class TestPow(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 5 ^ 3;')
        assert self.scopes[0]['x'] == 125


@pytest.mark.dependency(depends=['TestPow'])
class TestIPow(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 5; y = x ^= 3;')
        assert self.scopes[0]['x'] == 125
        assert self.scopes[0]['y'] == 125


@pytest.mark.dependency(depends=['TestSet'])
class TestEq(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 5 == 7;')
        assert self.scopes[0]['x'] == False

    def test_ints_2(self):
        self.run_gtp_block('x = 5 == 5;')
        assert self.scopes[0]['x'] == True

    def test_strs_1(self):
        self.run_gtp_block('x = "foo" == "bar";')
        assert self.scopes[0]['x'] == False

    def test_strs_2(self):
        self.run_gtp_block('x = "foo" == "foo";')
        assert self.scopes[0]['x'] == True


@pytest.mark.dependency(depends=['TestSet'])
class TestNe(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 5 != 7;')
        assert self.scopes[0]['x'] == True

    def test_ints_2(self):
        self.run_gtp_block('x = 5 != 5;')
        assert self.scopes[0]['x'] == False

    def test_strs_1(self):
        self.run_gtp_block('x = "foo" != "bar";')
        assert self.scopes[0]['x'] == True

    def test_strs_2(self):
        self.run_gtp_block('x = "foo" != "foo";')
        assert self.scopes[0]['x'] == False


@pytest.mark.dependency(depends=['TestSet'])
class TestLe(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 3 <= 5;')
        assert self.scopes[0]['x'] == True

    def test_ints_2(self):
        self.run_gtp_block('x = 5 <= 5;')
        assert self.scopes[0]['x'] == True

    def test_ints_3(self):
        self.run_gtp_block('x = 5 <= 3;')
        assert self.scopes[0]['x'] == False

    def test_strs_1(self):
        self.run_gtp_block("x = 'bar' <= 'foo';")
        assert self.scopes[0]['x'] == True

    def test_strs_2(self):
        self.run_gtp_block("x = 'foo' <= 'foo';")
        assert self.scopes[0]['x'] == True

    def test_strs_3(self):
        self.run_gtp_block("x = 'foo' <= 'bar';")
        assert self.scopes[0]['x'] == False


@pytest.mark.dependency(depends=['TestSet'])
class TestGe(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 3 >= 5;')
        assert self.scopes[0]['x'] == False

    def test_ints_2(self):
        self.run_gtp_block('x = 5 >= 5;')
        assert self.scopes[0]['x'] == True

    def test_ints_3(self):
        self.run_gtp_block('x = 5 >= 3;')
        assert self.scopes[0]['x'] == True

    def test_strs_1(self):
        self.run_gtp_block("x = 'bar' >= 'foo';")
        assert self.scopes[0]['x'] == False

    def test_strs_2(self):
        self.run_gtp_block("x = 'foo' >= 'foo';")
        assert self.scopes[0]['x'] == True

    def test_strs_3(self):
        self.run_gtp_block("x = 'foo' >= 'bar';")
        assert self.scopes[0]['x'] == True


@pytest.mark.dependency(depends=['TestSet'])
class TestLt(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 3 < 5;')
        assert self.scopes[0]['x'] == True

    def test_ints_2(self):
        self.run_gtp_block('x = 5 < 5;')
        assert self.scopes[0]['x'] == False

    def test_ints_3(self):
        self.run_gtp_block('x = 5 < 3;')
        assert self.scopes[0]['x'] == False

    def test_strs_1(self):
        self.run_gtp_block("x = 'bar' < 'foo';")
        assert self.scopes[0]['x'] == True

    def test_strs_2(self):
        self.run_gtp_block("x = 'foo' < 'foo';")
        assert self.scopes[0]['x'] == False

    def test_strs_3(self):
        self.run_gtp_block("x = 'foo' < 'bar';")
        assert self.scopes[0]['x'] == False


@pytest.mark.dependency(depends=['TestSet'])
class TestGt(GTPTester):

    def test_ints_1(self):
        self.run_gtp_block('x = 3 > 5;')
        assert self.scopes[0]['x'] == False

    def test_ints_2(self):
        self.run_gtp_block('x = 5 > 5;')
        assert self.scopes[0]['x'] == False

    def test_ints_3(self):
        self.run_gtp_block('x = 5 > 3;')
        assert self.scopes[0]['x'] == True

    def test_strs_1(self):
        self.run_gtp_block("x = 'bar' > 'foo';")
        assert self.scopes[0]['x'] == False

    def test_strs_2(self):
        self.run_gtp_block("x = 'foo' > 'foo';")
        assert self.scopes[0]['x'] == False

    def test_strs_3(self):
        self.run_gtp_block("x = 'foo' > 'bar';")
        assert self.scopes[0]['x'] == True


@pytest.mark.dependency(depends=['TestSet'])
class TestNot(GTPTester):

    def test_false(self):
        self.run_gtp_block('x = not false;')
        assert self.scopes[0]['x'] == True

    def test_true(self):
        self.run_gtp_block('x = not true;')
        assert self.scopes[0]['x'] == False
