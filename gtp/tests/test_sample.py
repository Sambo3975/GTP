from gtp.src.main import GTPBlock


class TestGTP:

    scopes = [dict()]
    readonlies = set()
    outputs = []

    def gtp_block(self, contents: str):
        return GTPBlock(self.scopes, self.readonlies, self.outputs, 0, 0, contents)

    # ASSIGNMENT

    def test_assignment_int_positive(self):
        self.gtp_block("x = 5;").run()
        assert self.scopes[0]['x'] == 5

    def test_assignment_int_negative(self):
        self.gtp_block("x = -17;").run()
        assert self.scopes[0]['x'] == -17

    def test_assignment_str_single(self):
        self.gtp_block("x = 'foo';").run()
        assert self.scopes[0]['x'] == 'foo'

    def test_assignment_str_double(self):
        self.gtp_block('x = "bar";').run()
        assert self.scopes[0]['x'] == 'bar'

    def test_assignment_true(self):
        self.gtp_block('x = true;').run()
        assert self.scopes[0]['x'] == True

    def test_assignment_false(self):
        self.gtp_block('x = false;').run()
        assert self.scopes[0]['x'] == False

    def test_assignment_null(self):
        self.gtp_block('x = null;').run()
        assert self.scopes[0]['x'] == None

    def test_assignment_var(self):
        self.gtp_block('x = 5; y = x;').run()
        assert self.scopes[0]['x'] == 5
        assert self.scopes[0]['x'] == self.scopes[0]['y']

    def test_assignment_fstr(self):
        self.gtp_block('x = "foo"; y = f"{5}\\ {x} fighters";').run()
        assert self.scopes[0]['y'] == "5 foo fighters"

    def test_assignment_fstr_esc(self):
        self.gtp_block('x = "bar"; y = f"\\{{x}}";').run()
        assert self.scopes[0]['y'] == "{bar}"

    def test_assignment_chained(self):
        self.gtp_block('x = y = 5;').run()
        assert self.scopes[0]['y'] == 5
        assert self.scopes[0]['x'] == self.scopes[0]['y']
