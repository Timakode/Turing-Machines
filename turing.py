import re


LAMBDA = 'λ'

# ОМТ
class Tape:
    # конвертирует число в подстрочный формат, чтобы корректно отображать состояние
    @staticmethod
    def toUnderline(num):
        result = ''
        while num >= 10:
            result = chr(8320 + num % 10) + result
            num //= 10
        result = chr(8320 + num) + result
        return result

    def __init__(self):
        self._word = LAMBDA
        self.index = 0

    # установка и получение текущего содержимого ленты
    @property
    def word(self):
        return self._word
    # при установке содержимого ленты индекс обнуляется
    @word.setter
    def word(self, word):
        self.index = 0
        if not word:
            self._word = LAMBDA
        else:
            self._word = word

    # для получения и установки символа на текущей позиции головки
    @property
    def char(self):
        return self._word[self.index]

    @char.setter
    def char(self, char):
        self._word = self._word[:self.index] + char + self._word[self.index + 1:]

    # для перемещения головки
    def move(self, direction):
        if direction == 'R':
            if self._word.startswith(LAMBDA):
                self._word = self._word[1:]
            else:
                self.index += 1
            if self.index == len(self._word):
                self._word += LAMBDA
        elif direction == 'L':
            if self.index > 0:
                self.index -= 1
                if self._word.endswith(LAMBDA):
                    self._word = self._word[:-1]
            elif self._word != LAMBDA:
                self._word = LAMBDA + self._word

    def review(self, state):
        if state != 'z':
            state = Tape.toUnderline(int(state))
        state = f'q{state}'
        return self._word[:self.index] + state + self._word[self.index:]

# ММТ
class MultiTape:
    def __init__(self, tapesCount):
        self.tapes = tuple(Tape() for _ in range(tapesCount))

    # установка и получение содержимого первой ленты
    @property
    def word(self):
        return self.tapes[0]._word

    @word.setter
    def word(self, word):
        self.tapes[0].word = word
        for tape in self.tapes[1:]:
            tape.word = ''

    # для получения и установки символов на текущих позициях всех лент
    @property
    def char(self):
        return tuple(tape.char for tape in self.tapes)

    @char.setter
    def char(self, char):
        for i, tape in enumerate(self.tapes):
            tape.char = char[i]

    # перемещает головки всех лент
    def move(self, directions):
        for i, tape in enumerate(self.tapes):
            tape.move(directions[i])

    # визуализация
    def review(self, state):
        return '\t'.join(tape.review(state) for tape in self.tapes)

# МТ
class Turing:
    COMMAND_REGEXP = re.compile(
        r'^q(\d+) (.) -> q(\d+|z) (.) ([LER])(?: +\#.+)?$' # регулярное выражение для разбора команд ОМТ
    )
    COMMAND_REGEXP_MULTITAPE = \
        r'^\(q(\d+)((?:,(?:.)){count})\) -> ' \
        r'\(q(\d+|z)((?:,(?:.)){count});' \
        r'([LER](?:,[LER]){count-1})\)(?: +\#.+)?$' # шаблон регулярного выражения для разбора команд ММТ

    def __init__(self, commands, tapesCount=1):
        self.tapesCount = tapesCount
        self.tapeObj = Tape() if tapesCount == 1 else MultiTape(tapesCount)
        self.commands = {}
        commands = commands.strip().splitlines()
        if tapesCount == 1:
            for command in commands:
                if command:
                    oldState, oldChar, state, char, direction = \
                        Turing.COMMAND_REGEXP.match(command).groups()
                    self.commands[oldState, oldChar] = state, char, direction
        else:
            Turing.COMMAND_REGEXP_MULTITAPE = re.compile(
                Turing.COMMAND_REGEXP_MULTITAPE
                .replace('count-1', str(tapesCount - 1))
                .replace('count', str(tapesCount))
            )
            for command in commands:
                if command:
                    oldState, oldChars, state, chars, directions = \
                        Turing.COMMAND_REGEXP_MULTITAPE.match(command).groups()
                    oldChars, chars, directions = map(
                        lambda str: str.split(','),
                        (oldChars, chars, directions)
                    )
                    self.commands[(oldState, tuple(oldChars[1:]))] = \
                        (state, tuple(chars[1:]), tuple(directions))

    # для обработки слова
    def processWord(self, word, verbose=False):
        state = '0'
        self.tapeObj.word = word
        iterCounter = 0
        while state != 'z' and \
                (command := self.commands.get((state, self.tapeObj.char))) is not None:
            iterCounter += 1
            if verbose:
                yield (self.tapeObj.review(state), iterCounter)
            state, self.tapeObj.char, direction = command
            self.tapeObj.move(direction)
        yield (
            (self.tapeObj.review(state) if verbose else self.tapeObj.word),
            iterCounter
        )
