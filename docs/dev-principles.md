# Development Principles (v2 onward)

These apply to all new code. v1 was written without them — v2 must not repeat that.

## Before writing

- **Interface first.** Write the function signature and return type before the body. Awkward to call = wrong design.
- **Failure cases first.** Ask "what can go wrong?" before "how does the happy path work?"
- **YAGNI.** Build what is needed now. Premature abstractions are harder to remove than to add.

## While writing

- **One thing does one thing.** A function that does two things is two functions. This is also what makes code testable.
- **Names over comments.** A well-named function needs no comment. A poorly named one needs a paragraph that will go stale.
- **TDD — failing test first.** No implementation without a test that defines the expected behavior. The test must be seen failing before the implementation is written. A test that was never red is untrustworthy.

## After writing

- **Read your own diff before every commit.** Treat it as reviewing someone else's code.
- **If it's not in a test, it doesn't exist.** After implementing, ask: "would a test catch a regression here?"

## Meta-principle

> Make the wrong thing hard to do and the right thing easy.
