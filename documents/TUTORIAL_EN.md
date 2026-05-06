# Lune v0.1 Tutorial (English)

This document is an English translation of `documents/TUTORIAL.md` (Japanese).

Let’s play with a small lazy evaluation language.

Lune is still an early, experimental language. Even so, it already has a few fun features:

- Python-like indentation-based syntax
- ML-like `fn`, `type`, and `match`
- Lazy-by-default evaluation
- Natural closures via partial application
- `Option` / `Result` / `List` built in from the start
- Lightweight `record` and field access
- `while` for small imperative loops
- `for` for natural list traversal
- A small type checker

In this tutorial, we’ll walk through the parts of Lune that are “fun to write”, using working code step by step.

## 1. First steps

Working directory:

```sh
cd lune_v0_1
```

If you want to try expressions and declarations interactively, the REPL is handy:

```sh
./bin/lune
```

Running `./bin/lune` with no arguments starts the REPL. If you want to evaluate a file, pass CLI arguments to the same script.

When started in a terminal, the REPL supports line editing like Bash:

- Move the cursor with left/right arrows.
- Browse history with up/down arrows.
- Edit with Backspace / Delete.
- Jump to the beginning/end with `Ctrl-A` / `Ctrl-E`.

If possible, history is saved to `~/.lune_history`. Being able to recall recent expressions with the up arrow makes experimentation much nicer.

To evaluate a file:

```sh
./bin/lune --eval answer samples/records.lune
```

To only type-check:

```sh
./bin/lune --check samples/records.lune
```

## 2. `let` is lazy

In Lune, `let` does not compute the value immediately. It waits until the value is needed.

```lune
let x = 1 + 2
let answer = x * 10
```

This looks normal. You can clearly see laziness if you put a failing expression somewhere:

```lune
let danger = crash()
let answer = 42
```

Even if you evaluate `answer`, `danger` is never used, so `crash()` is never evaluated.

```sh
./bin/lune --eval answer your_file.lune
```

Result:

```text
42
```

The intuition is closer to “placing a promise to compute later when needed” than “storing a value”.

## 3. Function arguments are lazy too

Function arguments are also lazy by default.

```lune
def first(a: Int, b: Int): Int =
    a

let answer = first(10, crash())
```

Since `first` does not use `b`, `crash()` is not evaluated.

```text
answer == 10
```

This is powerful for conditional computations and infinite data structures. It feels nice to not have to build what you won’t use.

## 4. Use `strict` to choose “evaluate now”

Sometimes laziness is great, and sometimes you want eager evaluation. In that case, use `strict` or `!`.

```lune
def ignore(a: Int, !b: Int): Int =
    a

let answer = ignore(10, crash())
```

Here, `b` is a strict argument, so `crash()` is evaluated when calling the function.

You can also use it for bindings:

```lune
strict let x = 1 + 2
```

In Lune, the basic stance is “lazy by default; strict only where needed”.

## 5. `lazy` and `force`

If you want to explicitly create a delayed value, use `lazy`.

```lune
let delayed = lazy (1 + 2)
let answer = force delayed
```

The type of `delayed` is `Lazy[Int]`, and `answer` is `Int`.

You can also write it as a multi-line block:

```lune
let delayed = lazy:
    let x = 40
    x + 2

let answer = force delayed
```

Think of `lazy` as “a box you can open later”. When you `force` it, the contents are computed.

## 6. Memoized thunks

Once a delayed value is evaluated, it remembers the result.

In this chapter we use `tick()` and `tickCount()` for observation:

- `tick()` increments an internal counter each time it is called, and returns the new value.
- `tickCount()` returns the current counter value.

These are helper functions for observing laziness. They are not something you would actively use in normal application logic.

```lune
let x = tick()
let answer = x + x
let count = tickCount()
```

Even though `x` is used twice, `tick()` is executed only once.

```text
answer == 2
count == 1
```

If `tick()` had been executed twice, `answer` would have been `1 + 2` (so `3`), and `count` would have been `2`. In reality, when `x` is needed the first time, its thunk runs `tick()` once and stores the result `1`. The second `x` just reads the stored `1`.

You can try this in the REPL too:

```text
lune> let x = tick()
ok
lune> x + x
2 : Int
lune> tickCount()
1 : Int
```

`tickCount()` itself does not increment the counter. It’s a window into how many times `tick()` was actually executed.

This combination of “wait until needed” and “remember once computed” is the core of Lune’s lazy evaluation.

## 7. `fn` and partial application

Write lambdas with `fn`:

```lune
let add = fn x y -> x + y
let answer = add(20, 22)
```

Partial application also works:

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

`add` normally takes two arguments, but `add(1)` (passing only one argument) returns “a function that adds 1 once it receives the remaining argument”.

So you can easily build small helpers like these:

```lune
let double = fn x -> x * 2
let add10 = fn x -> x + 10

let answer = add10(double(16))
```

In the future, there’s room to combine this with something like `|>` to make pipelines feel even better.

## 8. Algebraic data types for “shapes”

Lune has algebraic data types (often abbreviated as ADTs).

The name sounds grand, but at first it’s enough to think of it as “a way to enumerate the possible shapes a value can take, as a type”.

```lune
type Option[T] =
    | Some(value: T)
    | None
```

This `Option[T]` is a type with two possible shapes:

- `Some(value)` means “there is a value”.
- `None` means “there is no value”.

You can represent “maybe there is a value, maybe not” with a type rather than `null`.

```lune
let good = Some(42)
let empty = None
```

To extract, use `match`:

```lune
def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue

let answer = getOrElse(Some(42), 0)
```

`match` is syntax for branching based on the shape of a value.

## 9. Pattern matching reads well

Let’s look at another example:

```lune
type Shape =
    | Circle(radius: Int)
    | Rect(width: Int, height: Int)

def area(shape: Shape): Int =
    match shape:
        | Circle(radius) -> radius * radius * 3
        | Rect(width, height) -> width * height

let answer = area(Rect(6, 7))
```

Instead of checking “which kind is it?” with `if`, you can write the logic directly as “for this shape, do this”.

ADTs and `match` are where Lune’s functional style shows up strongly.

## 10. Records for named data

If you just want to bundle multiple values, `record` is convenient:

```lune
record User:
    name: String
    age: Int

let ada = User(name = "Ada", age = 36)
let answer = ada.age + 6
```

Access fields with `.`:

```lune
let name = ada.name
let age = ada.age
```

Generic records also work:

```lune
record Box[T]:
    value: T

let boxed = Box(value = 42)
let answer = boxed.value
```

In the REPL, record values are displayed in a field-centric shape:

```text
lune> ada
{ name = "Ada", age = 36 } : User
```

Normal record fields are also lazy. Unused fields are not evaluated.

```lune
record User:
    name: String
    age: Int

let ada = User(name = crash(), age = 36)
let answer = ada.age
```

In this case, `name` is never referenced, so `crash()` is not evaluated.

## 11. Small standard library tools

In Lune v0.1, a few useful types and functions are available from the start:

```lune
let xs = (1 2 3 4)
let doubled = map(xs, fn x -> x * 2)
let total = fold(doubled, 0, fn acc x -> acc + x)
let answer = total
```

`(1 2 3 4)` is a Lisp-style list literal. You can type it in the same shape you see when lists are printed. `[1, 2, 3, 4]` means the same thing.

Both let you create a finite list naturally and concisely, instead of writing `Cons(1, Cons(2, Cons(3, Cons(4, Nil))))`.

The empty list is `[]`. Since `()` is `Unit`, it’s best to keep those separate.

`range(1, 5)` also creates a list of `1, 2, 3, 4`.

In the REPL, lists are displayed in Lisp style:

```text
lune> [1, 2, 3, 4]
(1 2 3 4) : List[Int]
lune> (1 2 3 4)
(1 2 3 4) : List[Int]
lune> "Ada"
"Ada" : String
```

Strings are displayed with double quotes, so they remain readable even inside lists or records.

Elements of list literals are also lazy:

```lune
let items = [1, crash()]
let answer = head(items)
```

`answer` is `Some(1)`. The second element stays asleep until it’s needed.

### A basic set of list operations

If you remember these 7, you can write quite a lot of list processing in Lune:

```lune
map(list, fn x -> ...)
filter(list, fn x -> ...)
fold(list, initial, fn acc x -> ...)
take(list, count)
drop(list, count)
head(list)
tail(list)
```

`map` transforms each element:

```lune
let numbers = [1, 2, 3, 4]
let doubled = map(numbers, fn x -> x * 2)
```

REPL:

```text
lune> doubled
(2 4 6 8) : List[Int]
```

`filter` keeps only elements that satisfy a predicate:

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let evens = filter(numbers, fn x -> x % 2 == 0)
```

```text
lune> evens
(2 4 6) : List[Int]
```

`fold` reduces a list into a single value. It’s useful for sums, maxima, stringification, and more:

```lune
let numbers = [1, 2, 3, 4]
let total = fold(numbers, 0, fn acc x -> acc + x)
```

`acc` is “the result so far”. It starts at `0`, then `1`, then `3`, then `6`, and finally `10`.

`take` and `drop` slice a list from the front:

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let firstThree = take(numbers, 3)
let afterThree = drop(numbers, 3)
```

```text
lune> firstThree
(1 2 3) : List[Int]
lune> afterThree
(4 5 6) : List[Int]
```

You can write paging-like logic too:

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let page1 = take(numbers, 2)
let page2 = take(drop(numbers, 2), 2)
let page3 = take(drop(numbers, 4), 2)
```

`head` and `tail` safely extract the first element and the rest. Because lists can be empty, the return type is `Option`.

```lune
let numbers = [1, 2, 3]
let first = head(numbers)
let rest = tail(numbers)
let missing = head([])
```

```text
lune> first
Some(1) : Option[Int]
lune> rest
Some((2 3)) : Option[List[Int]]
lune> missing
None : Option[Any]
```

When you want to use the value directly, `getOrElse` is convenient:

```lune
let firstNumber = getOrElse(head([10, 20]), 0)
let emptyNumber = getOrElse(head([]), 0)
```

`firstNumber` is `10`, and `emptyNumber` is `0`.

### Combining them

List functions feel best when you combine them:

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let answer =
    fold(
        map(
            filter(numbers, fn x -> x % 2 == 0),
            fn x -> x * 10
        ),
        0,
        fn acc x -> acc + x
    )
```

This pipeline is: “keep only evens”, “multiply by 10”, “sum”. The `answer` is `120`.

When combined with `record`, it becomes more practical:

```lune
record User:
    name: String
    age: Int

let users = [
    User(name = "Ada", age = 36),
    User(name = "Grace", age = 85),
    User(name = "Linus", age = 55),
]

let names = map(users, fn user: User -> user.name)
let elders = filter(users, fn user: User -> user.age >= 60)
let elderNames = map(elders, fn user: User -> user.name)
let totalAge = fold(users, 0, fn acc: Int user: User -> acc + user.age)
```

```text
lune> names
("Ada" "Grace" "Linus") : List[String]
lune> elderNames
("Grace") : List[String]
lune> totalAge
176 : Int
```

### Laziness and list functions

`take` extracts only as much as needed. `take(list, 0)` does not evaluate the list at all:

```lune
let safe = take(crash(), 0)
```

This can be treated as `()`, i.e. an empty list.

Also, the tail of the list returned by `take` remains lazy:

```lune
let one = take([1, crash()], 1)
```

```text
lune> one
(1) : List[Int]
```

The second element is not part of the result, so it is not evaluated. Laziness is very easy to feel here.

### Sample file

A more complete example for this chapter is in `samples/list_tools.lune`:

```sh
./bin/lune --check samples/list_tools.lune
./bin/lune --eval doubled samples/list_tools.lune
./bin/lune --eval adultNames samples/list_tools.lune
```

`Option` is built in too:

```lune
let value = Some(42)
let answer = getOrElse(value, 0)
```

The standard library is still small, but “not having to define `Option` and `List` from scratch every time” already makes experimentation much easier.

## 12. Write small loops with `while`

Lune values functional features, but for small repetitive tasks you can also use `while`:

```lune
let answer =
    var i = 0
    var total = 0
    while i < 5:
        total = total + i
        i = i + 1
    total
```

Since this computes `0 + 1 + 2 + 3 + 4`, `answer` becomes `10`.

The `while` condition is evaluated every time. When it becomes `false`, the loop stops. `while` itself returns `Unit`.

```lune
let answer =
    var i = 0
    while i < 3:
        i = i + 1
    i
```

Here, `answer` is `3`.

The interaction with laziness matters too. If the condition is `false` from the beginning, the body is not executed:

```lune
let answer =
    while false:
        crash()
    42
```

In this case, `crash()` is not evaluated.

`while` is convenient, but for Lune-style data transformations, `map`, `filter`, and `fold` can be more readable. It feels good to use `while` for small procedures and functions for data flow.

You can also write the same logic with recursion:

```lune
def sumUntil(i: Int, end: Int, total: Int): Int =
    if i >= end then total else sumUntil(i + 1, end, total + i)

let answer = sumUntil(0, 5, 0)
```

This `answer` is also `10`.

The `while` version can be easier for a first-time reader because it updates variables step by step. The recursive version passes state through arguments; it’s more functional and often easier to test as a small reusable component.

In Lune you can choose either. Use `while` for small procedures, and recursion or `fold` for value transformations and reusable computations.

## 13. Walk a list with `for`

`while` repeats while a condition holds. If you just want to process a list in order, `for` is more concise:

```lune
let answer =
    var total = 0
    for x in [1, 2, 3, 4]:
        total = total + x
    total
```

Since `[1, 2, 3, 4]` is `(1 2 3 4)`, `answer` is `10`.

`for` is a small construct dedicated to `List[T]`. Writing `for x in items:` binds each element to `x` and executes the body. `for` itself returns `Unit`, so in the example above we put `total` at the end to produce the final answer.

You can use patterns too:

```lune
let pairs = [(1, 10), (2, 20)]

let answer =
    var total = 0
    for (left, right) in pairs:
        total = total + left + right
    total
```

Each tuple element is split into `left` and `right`. In this example, `answer` is `33`.

Let’s also look at the interaction with laziness:

```lune
let answer =
    for _ in Nil:
        crash()
    42
```

With an empty list, the body is not executed, so `crash()` is not evaluated. `for` advances by checking whether the list is `Cons` or `Nil` one step at a time. The element contents are evaluated only when they become needed by a pattern or the body.

`for` is good for readable aggregations and side-effect-like processing. On the other hand, to create a new list use `map`; to narrow by a condition use `filter`; to reduce into a value use `fold`.

## 14. Split into modules

Once things get a bit bigger, you can split code into files.

`math.lune`:

```lune
module math

def add(x: Int, y: Int): Int =
    x + y
```

`main.lune`:

```lune
module main
import math

let answer = add(20, 22)
```

Run:

```sh
./bin/lune --eval answer main.lune
```

In v0.1, the top-level names of imported modules are brought into the same environment. So you write `add` rather than `math.add`.

## 15. Try type checking

Lune has a small type checker:

```lune
let answer: Int = true
```

This is a type error.

```sh
./bin/lune --check bad.lune
```

Errors are displayed with code positions.

The type checker is not complete yet, but it already catches a lot of basic mistakes.

## 16. Write a small program

Finally, here’s an example that combines several features:

```lune
module tutorial

record User:
    name: String
    age: Int

type Greeting =
    | Greeting(text: String)

def adultLabel(user: User): String =
    if user.age >= 20 then "adult" else "young"

def greet(user: User): Greeting =
    Greeting("Hello, " + user.name + " (" + adultLabel(user) + ")")

def render(greeting: Greeting): String =
    match greeting:
        | Greeting(text) -> text

def birthdayMessage(user: User): String =
    var years = 0
    while years < 1:
        years = years + 1
    "next year: " + user.name

let ada = User(name = "Ada", age = 36)
let answer = render(greet(ada))
```

Evaluate:

```sh
./bin/lune --eval answer tutorial.lune
```

Result:

```text
'Hello, Ada (adult)'
```

You can start to see the shape of it: Lune is a language where “data shapes are expressed by types, only what’s needed is evaluated, and values are decomposed readably with `match`”.

`birthdayMessage` is a slightly contrived example, but it shows that `while` can be used inside a normal block. Similarly, when you want to process a list, `for` can also be used inside a block.

## 17. Exercises

1. Create `record Book` with `title: String` and `pages: Int`.
2. Create `isLong(book: Book): Bool` that returns `true` when the book has 300 pages or more.
3. Create `type MaybeLong = LongBook(title: String) | ShortBook(title: String)`.
4. Create `classify(book: Book): MaybeLong`, and use `match` to convert it to a display string.
5. Try reading only `pages` from `Book(title = crash(), pages = 100)`. What happens?
6. Using `while`, compute the sum from `1` to `10`.
7. Using `for` and `[1, 2, 3, 4, 5]`, compute the sum.
8. In the REPL, use the up arrow to recall the previous expression, edit it slightly, and re-run it.

That last exercise is very Lune-like: what you don’t use is still asleep.

## 18. Current limitations

Lune v0.1 is still an early version.

Some notable unsupported items:

- class / interface
- Real Java calls
- record update
- record pattern
- mutable record field
- `try` / `catch`
- `for`
- `break` / `continue`
- LSP / formatter / package manager

But the core feeling is already there:

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

In this small expression, Lune’s direction is packed in.

Delay evaluation, evaluate when needed, pass functions as values, and express data shapes with types.  
From here, we’ll grow the language little by little.

