# Lune v0.1 Tutorial

Let's play with a small lazy-evaluation language.

Lune is still an experimental language in its early stages. Even so, it already has some fun features.

- Python-style indentation syntax.
- ML-style `fn`, `type`, and `match`.
- Lazy evaluation by default.
- Closures created naturally via partial application.
- `Option` / `Result` / `List` available out of the box.
- Lightweight `record` with field access.
- Small imperative loops with `while`.
- Natural list traversal with `for`.
- A small type checker included.

This tutorial walks through the "fun parts of writing Lune" with actual working code.

## 1. First Steps

Working directory:

```sh
cd lune_v0_1
```

For trying expressions and declarations, the REPL is handy.

```sh
./bin/lune
```

Running `./bin/lune` with no arguments starts the REPL. To evaluate a file, pass CLI arguments to the same script.

The REPL started in a terminal supports line editing similar to a Bash command line.

- Arrow keys to move the cursor left and right.
- Up/down arrow keys to navigate history.
- Backspace / Delete to edit.
- `Ctrl-A` to jump to the beginning of the line, `Ctrl-E` to the end.

History is saved to `~/.lune_history` when possible. Being able to recall a recently tried expression with the up key makes experimentation much easier.

To evaluate a file:

```sh
./bin/lune --eval answer samples/records.lune
```

To only type-check:

```sh
./bin/lune --check samples/records.lune
```

## 2. `let` Is Lazy

Lune's `let` does not compute a value immediately — it waits until the value is needed.

```lune
let x = 1 + 2
let answer = x * 10
```

This looks ordinary. But you can see lazy evaluation at work by placing a failing expression:

```lune
let danger = crash()
let answer = 42
```

Evaluating `answer` never uses `danger`, so `crash()` is never evaluated.

```sh
./bin/lune --eval answer your_file.lune
```

Result:

```text
42
```

The intuition for lazy evaluation is less "place a value here" and more "place a promise to compute when needed."

## 3. Function Arguments Are Also Lazy

Function arguments are also lazy by default.

```lune
def first(a: Int, b: Int): Int =
    a

let answer = first(10, crash())
```

Since `first` never uses `b`, `crash()` is never evaluated.

```text
answer == 10
```

This is powerful when dealing with conditional computation or infinite data structures — you don't have to build things you won't use.

## 4. `strict` for "Evaluate Now"

Sometimes laziness is welcome; other times you want immediate evaluation. For those cases, use `strict` or `!`.

```lune
def ignore(a: Int, !b: Int): Int =
    a

let answer = ignore(10, crash())
```

Here, `b` is a strict argument, so `crash()` is evaluated at the call site.

You can also use it on bindings:

```lune
strict let x = 1 + 2
```

In Lune, the pattern is "lazy by default, strict only where needed."

## 5. `lazy` and `force`

When you want to create a lazy value explicitly, use `lazy`.

```lune
let delayed = lazy (1 + 2)
let answer = force delayed
```

The type of `delayed` is `Lazy[Int]`, and `answer` is `Int`.

Multi-line form also works:

```lune
let delayed = lazy:
    let x = 40
    x + 2

let answer = force delayed
```

Think of `lazy` as a box you open later. `force` computes the contents.

## 6. Memoized Thunks

A lazy value remembers its result once evaluated.

This chapter uses `tick()` and `tickCount()` as observation tools.

- `tick()` increments an internal counter each time it's called and returns the new value.
- `tickCount()` returns the current counter value.

Both are helper functions for observing lazy evaluation behavior. They are not meant for regular application logic.

```lune
let x = tick()
let answer = x + x
let count = tickCount()
```

Although `x` is used twice, `tick()` executes only once.

```text
answer == 2
count == 1
```

If `tick()` had run twice, `answer` would be `1 + 2 = 3` and `count` would be `2`. In reality, the thunk for `x` runs `tick()` once when first needed, saves the result `1`, and subsequent uses of `x` just read the saved value.

You can try this in the REPL:

```text
lune> let x = tick()
ok
lune> x + x
2 : Int
lune> tickCount()
1 : Int
```

`tickCount()` itself does not increment the counter — it's a window to see how many times `tick()` actually ran.

This combination of "wait until needed" and "remember once computed" is the core of Lune's lazy evaluation.

## 7. `fn` and Partial Application

Lambdas are written with `fn`.

```lune
let add = fn x y -> x + y
let answer = add(20, 22)
```

Partial application is also supported:

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

`add` normally takes two arguments, but `add(1)` — passing only one — returns "a function that takes one more argument and then adds." This makes it easy to build small utility functions:

```lune
let double = fn x -> x * 2
let add10 = fn x -> x + 10

let answer = add10(double(16))
```

In the future, combining these with `|>` could make the style even more expressive.

## 8. Algebraic Data Types for Modeling Shapes

Lune supports algebraic data types (ADTs). The name sounds intimidating, but at first you can think of them simply as "a way to list out the possible shapes a value can take."

```lune
type Option[T] =
    | Some(value: T)
    | None
```

`Option[T]` is a type with two possible shapes:

- `Some(value)` — "there is a value."
- `None` — "there is no value."

This lets you represent "might have a value, might not" with a type instead of `null`.

```lune
let good = Some(42)
let empty = None
```

Use `match` to extract values:

```lune
def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue

let answer = getOrElse(Some(42), 0)
```

`match` is the syntax for branching based on the shape of a value.

## 9. Pattern Matching Is Readable

Let's look at a few more examples.

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

Instead of using `if` to check the kind, you write directly "if this shape, then this." Algebraic data types and `match` are where Lune's functional nature shines.

## 10. Records for Named Data

When you just want to group multiple values together, `record` is handy.

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

Generic records work too:

```lune
record Box[T]:
    value: T

let boxed = Box(value = 42)
let answer = boxed.value
```

In the REPL, record values display in a field-centric format:

```text
lune> ada
{ name = "Ada", age = 36 } : User
```

Regular record fields are also lazy — unused fields are never evaluated.

```lune
record User:
    name: String
    age: Int

let ada = User(name = crash(), age = 36)
let answer = ada.age
```

Since `name` is never accessed, `crash()` is never evaluated.

## 11. Small Tools from the Standard Library

Lune v0.1 comes with several useful types and functions out of the box.

```lune
let xs = (1 2 3 4)
let doubled = map(xs, fn x -> x * 2)
let total = fold(doubled, 0, fn acc x -> acc + x)
let answer = total
```

`(1 2 3 4)` is a Lisp-style list literal. `[1, 2, 3, 4]` means the same thing.

Both are short, natural ways to create finite lists instead of writing `Cons(1, Cons(2, Cons(3, Cons(4, Nil))))`.

The empty list is `[]`. Note that `()` means `Unit`, so these are distinct.

`range(1, 5)` also creates the list `1, 2, 3, 4`.

The REPL displays lists in Lisp style:

```text
lune> [1, 2, 3, 4]
(1 2 3 4) : List[Int]
lune> (1 2 3 4)
(1 2 3 4) : List[Int]
lune> "Ada"
"Ada" : String
```

Strings are displayed with double quotes, making them easy to read inside lists and records.

List literal elements are also lazy:

```lune
let items = [1, crash()]
let answer = head(items)
```

`answer` is `Some(1)`. The second element stays asleep until needed.

### Core List Operations

These 7 functions cover a lot of ground for list processing in Lune:

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

`filter` keeps only elements that match a condition:

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let evens = filter(numbers, fn x -> x % 2 == 0)
```

```text
lune> evens
(2 4 6) : List[Int]
```

`fold` reduces a list to a single value — useful for sums, max values, stringification, etc.:

```lune
let numbers = [1, 2, 3, 4]
let total = fold(numbers, 0, fn acc x -> acc + x)
```

`acc` is "the result so far": starts at `0`, then `1`, `3`, `6`, and finally `10`.

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

You can implement paging:

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let page1 = take(numbers, 2)
let page2 = take(drop(numbers, 2), 2)
let page3 = take(drop(numbers, 4), 2)
```

`head` and `tail` safely retrieve the first element and the rest. Since an empty list is possible, both return `Option`:

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

`getOrElse` is handy when you need the actual value:

```lune
let firstNumber = getOrElse(head([10, 20]), 0)
let emptyNumber = getOrElse(head([]), 0)
```

`firstNumber` is `10`, `emptyNumber` is `0`.

### Combining Them

List functions become most satisfying when combined:

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

This pipeline "keeps only evens" → "multiplies by 10" → "sums". `answer` is `120`.

Combining with `record` leads to more practical code:

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

### Lazy Evaluation and List Functions

`take` is a tool for retrieving only what you need. `take(list, 0)` does not evaluate the list at all:

```lune
let safe = take(crash(), 0)
```

This is treated as `()` — an empty list.

Furthermore, the tail of the list returned by `take` is also lazy:

```lune
let one = take([1, crash()], 1)
```

```text
lune> one
(1) : List[Int]
```

The second element is not included in the result, so it's never evaluated. Lazy evaluation is very tangible here.

### Sample File

A comprehensive example for this chapter is in `samples/list_tools.lune`:

```sh
./bin/lune --check samples/list_tools.lune
./bin/lune --eval doubled samples/list_tools.lune
./bin/lune --eval adultNames samples/list_tools.lune
```

`Option` is also built in:

```lune
let value = Some(42)
let answer = getOrElse(value, 0)
```

The standard library is still small, but just not having to define `Option` or `List` yourself every time makes experimentation much more pleasant.

## 12. Small Loops with `while`

Lune values functional features, but `while` is available for simple iteration too.

```lune
let answer =
    var i = 0
    var total = 0
    while i < 5:
        total = total + i
        i = i + 1
    total
```

`answer` is `0 + 1 + 2 + 3 + 4 = 10`.

The `while` condition is evaluated each iteration. When the condition becomes `false`, the loop exits and `while` itself returns `Unit`.

```lune
let answer =
    var i = 0
    while i < 3:
        i = i + 1
    i
```

Here `answer` is `3`.

The relationship with lazy evaluation is important: if the condition is `false` from the start, the body is never executed.

```lune
let answer =
    while false:
        crash()
    42
```

`crash()` is never evaluated here.

`while` is convenient, but for Lune-style data transformations, `map`, `filter`, and `fold` are often more readable. A good rule of thumb: `while` for small procedures, functions for data flow.

The same computation can be written recursively:

```lune
def sumUntil(i: Int, end: Int, total: Int): Int =
    if i >= end then total else sumUntil(i + 1, end, total + i)

let answer = sumUntil(0, 5, 0)
```

This `answer` is also `10`.

The `while` version follows steps with mutable variables, which can be easier for new readers. The recursive version passes state as arguments — more functional, easier to test as a small unit.

Lune lets you choose either. A good heuristic: `while` for small procedures, recursion or `fold` for value transformations and reusable computations.

## 13. Walking a List with `for`

`while` repeats as long as a condition holds. When you simply want to process a list in order, `for` is cleaner.

```lune
let answer =
    var total = 0
    for x in [1, 2, 3, 4]:
        total = total + x
    total
```

Since `[1, 2, 3, 4]` is `(1 2 3 4)`, `answer` is `10`.

`for` is a small syntax dedicated to `List[T]`. Writing `for x in items:` binds each element to `x` and executes the body. `for` itself returns `Unit`, so in the example above `total` is placed last to serve as the result.

Patterns work too:

```lune
let pairs = [(1, 10), (2, 20)]

let answer =
    var total = 0
    for (left, right) in pairs:
        total = total + left + right
    total
```

Each tuple's elements are destructured into `left` and `right`. This `answer` is `33`.

The relationship with lazy evaluation: when the list is empty, the body never executes.

```lune
let answer =
    for _ in Nil:
        crash()
    42
```

`crash()` is never evaluated. `for` advances one step at a time, checking `Cons` vs `Nil`. Element contents are evaluated when needed by the pattern or body.

`for` is well-suited for readable aggregation and side-effectful processing. For building a new list from a list, `map` is great; for filtering, `filter`; for reducing to a value, `fold`.

## 14. Splitting into Modules

When your code grows, you can split it into files.

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

In v0.1, top-level names from imported modules are brought into the same environment. So you write `add`, not `math.add`.

## 15. Type Checking

Lune has a small type checker.

```lune
let answer: Int = true
```

This is a type error.

```sh
./bin/lune --check bad.lune
```

Errors are displayed with code locations.

The type checker is not yet complete, but it catches many basic mistakes.

## 16. Writing a Small Program

Here is an example that brings several features together:

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

It's starting to take shape. Lune is a language where you "model data shapes with types, evaluate only what you need, and decompose readably with `match`."

`birthdayMessage` is a slightly contrived example, but it shows that `while` works naturally inside a block. Likewise, `for` can be used inside a block wherever list traversal is needed.

## 17. Exercises

1. Create a `record Book` with fields `title: String` and `pages: Int`.
2. Write `isLong(book: Book): Bool` that returns `true` for books with 300 or more pages.
3. Create `type MaybeLong = LongBook(title: String) | ShortBook(title: String)`.
4. Write `classify(book: Book): MaybeLong` and convert it to a display string with `match`.
5. Try reading only `pages` from `Book(title = crash(), pages = 100)` and see what happens.
6. Use `while` to compute the sum of `1` through `10`.
7. Use `for` and `[1, 2, 3, 4, 5]` to compute the sum.
8. In the REPL, use the up arrow to recall a previous expression, edit it slightly, and re-run it.

The last exercise captures something essential about this language: what you don't use is still sleeping.

## 18. Current Limitations

Lune v0.1 is still an early version.

Notable missing features:

- class / interface.
- Native Java interop.
- Record update syntax.
- Record patterns.
- Mutable record fields.
- `try` / `catch`.
- `break` / `continue`.
- LSP / formatter / package manager.

But the core feeling is already there:

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

This small expression captures the direction of Lune.

Lazy evaluation, evaluate only when needed, pass functions as values, model data shapes with types.  
From here, the language grows, one small step at a time.
