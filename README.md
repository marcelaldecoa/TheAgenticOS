# The Agentic OS

**An Operating System Model for Governed Agency**

> *The next abstraction in software is not the agent. It is the operating system around agency.*

---

## About This Book

This book proposes a new abstraction for intelligent software: the **Agentic OS** — an operating system model for agentic systems that brings the same rigor, structure, and design principles that made traditional operating systems successful.

Rather than treating agents as chatbots with tools, it frames them as governed operational systems composed of a cognitive kernel, isolated process fabric, layered memory, operator fabric, and a governance plane. From first principles to design patterns to reference architectures, the book explores how to build systems that solve problems through intention, reasoning, action, and adaptation — with performance, safety, extensibility, and reuse in mind.

## Structure

| Part | Chapters | Focus |
|------|----------|-------|
| **I — Theory and Foundations** | 01–05 | The shift from code execution to intent execution, why OS is the right analogy |
| **II — The Agentic OS Model** | 06–12 | Core architecture: kernel, process fabric, memory plane, operator fabric, governance |
| **III — Design Patterns** | 13–19 | Reusable patterns: kernel, process, memory, operator, governance, runtime, evolution |
| **IV — Solving Problems** | 20–24 | Intent interpretation, decomposition, plan-act-check-adapt, agent topologies, safety |
| **V — Building the System** | 25–29 | Reference architecture, boundaries, building blocks, extensibility, performance |
| **VI — Case Studies** | 30–34 | Coding OS, Research OS, Support OS, Knowledge OS, Multi-OS coordination |
| **VII — Toward a New Discipline** | 35–37 | Intent engineering, responsible agency, the future of operational intelligence |

## Read Online

The book is published at: **[https://marcelaldecoa.github.io/TheAgenticOS](https://marcelaldecoa.github.io/TheAgenticOS)**

## Run Locally

### Prerequisites

Install [mdBook](https://rust-lang.github.io/mdBook/guide/installation.html):

```bash
# With Cargo (Rust)
cargo install mdbook

# With Homebrew (macOS)
brew install mdbook

# With Scoop (Windows)
scoop install mdbook

# Or download a prebuilt binary from:
# https://github.com/rust-lang/mdBook/releases
```

### Build

```bash
# Clone the repository
git clone https://github.com/marcelaldecoa/TheAgenticOS.git
cd TheAgenticOS

# Build the book
mdbook build

# The output is in the `book/` directory
```

### Serve Locally (with live reload)

```bash
mdbook serve --open
```

This starts a local server at `http://localhost:3000` and opens it in your browser. Changes to any `.md` file will automatically reload the page.

### Watch for Changes (build only)

```bash
mdbook watch
```

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes before submitting a pull request.

## License

This work is licensed under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).
