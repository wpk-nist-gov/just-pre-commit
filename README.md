# just-pre-commit

[pre-commit]: https://pre-commit.com/
[just]: https://github.com/casey/just

A [pre-commit] hook for [just]. The primary purpose is to provide a hook to
format justfiles.

## Hooks

```yaml
repos:
  - repo: https://github.com/wpk-nist-gov/just-pre-commit
    rev: v1.35.0
    hooks:
      # Run just --fmt on justfiles
      - id: justfile-format
        # optionally pass extras arguments to just --fmt using:
        # extra_args: ["some", "options", "to", "just", "--" ]
        # include "--" to indicate proceeding options are to just
      # Run just commands
      - id: just
        extra_args: [my-just-command]
        # potentially useful options are:
        # pass_filenames: true/false
        # extra_args: [ "command-name" ]
        # types: [python]
        # always_run: true
```
