# Testing & Refactoring Plan - TDD Approach

## Overview

This plan refactors the Whisper GUI to support pluggable IPC mechanisms while maintaining backward compatibility. The current FIFO-based command control will be abstracted into an interface, allowing D-Bus or other mechanisms to be used as alternatives.

## Architecture

### Current State
- GUI directly creates and manages FIFO at `~/.whisper/control.fifo`
- FIFO reader thread in GUI reads commands and emits Qt signals
- Commands: "toggle", "start", "stop"

### Desired State (After Refactoring)
```
┌─────────────────────────────────────────────────┐
│ WhisperGUI                                       │
│  - Uses CommandController interface              │
│  - No knowledge of IPC implementation details    │
└──────────────┬──────────────────────────────────┘
               │ uses
               │
        ┌──────▼──────────────────┐
        │ CommandController       │
        │ (Abstract Interface)    │
        └──────┬──────────────────┘
               │
        ┌──────┴───────┬──────────────────────┐
        │              │                       │
    ┌───▼────────┐ ┌──▼──────────┐ ┌────────▼──────┐
    │ FIFOImpl    │ │ DBusImpl     │ │ SocketImpl    │
    │ (FIFO)     │ │ (D-Bus)     │ │ (Sockets)    │
    └────────────┘ └─────────────┘ └──────────────┘
```

## Phase 1: Design IPC Abstraction Layer

### 1.1: Create Abstract Interface

**File:** `src/whisper_app/ipc_controller.py`

```python
from abc import ABC, abstractmethod
from typing import Callable, Optional

class CommandController(ABC):
    """Abstract interface for external command control.

    Implementations can use FIFO, D-Bus, sockets, etc.
    All commands are routed through signals to the main Qt thread.
    """

    @abstractmethod
    def start(self) -> None:
        """Start listening for commands."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening for commands."""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if controller is running."""
        pass

    # Signal callbacks
    def on_command(self, command: str) -> None:
        """Override to handle commands. Subclasses should emit signals."""
        pass
```

### 1.2: Create FIFO Implementation

**File:** `src/whisper_app/fifo_controller.py`

Wraps current FIFO logic into the CommandController interface.

### 1.3: Create D-Bus Implementation (Stub)

**File:** `src/whisper_app/dbus_controller.py`

Implements same interface using D-Bus instead of FIFO.

## Phase 2-3: Testing Strategy

### Test Categories

1. **Interface Tests** (test_ipc_controller.py)
   - Test abstract interface contracts
   - Ensure all implementations follow interface

2. **FIFO Implementation Tests** (test_fifo_controller.py)
   - Mock file operations
   - Test command parsing
   - Test error handling
   - Test thread lifecycle

3. **D-Bus Implementation Tests** (test_dbus_controller.py)
   - Mock D-Bus library
   - Test signal emission
   - Test D-Bus registration
   - Test error handling

4. **Integration Tests** (test_gui_with_controller.py)
   - GUI with different controllers
   - Command flow: external → controller → GUI
   - Signal handling

5. **End-to-End Tests** (test_e2e.py)
   - Real FIFO or mock D-Bus
   - Full recording cycle triggered by commands

## Phase 4: Refactoring Strategy

### Step 1: Create abstraction (Phase 1)
### Step 2: Write tests for abstraction (Phase 5)
### Step 3: Implement FIFO controller (Phase 2)
### Step 4: Refactor GUI to use FIFO controller (Phase 4)
### Step 5: Implement D-Bus controller (Phase 3)
### Step 6: Add more GUI tests (Phase 9)
### Step 7: Run full test suite (Phase 10)

## Key Design Decisions

1. **Backward Compatibility**: FIFO remains default, no breaking changes
2. **Zero Dependencies**: No new external dependencies required
3. **Testability**: All components use dependency injection
4. **Flexibility**: Easy to add new IPC mechanisms

## Files to Create/Modify

### New Files
- `src/whisper_app/ipc_controller.py` - Abstract interface
- `src/whisper_app/fifo_controller.py` - FIFO implementation
- `src/whisper_app/dbus_controller.py` - D-Bus implementation (stub)
- `tests/test_ipc_controller.py` - Interface tests
- `tests/test_fifo_controller.py` - FIFO tests
- `tests/test_dbus_controller.py` - D-Bus tests
- `tests/test_gui_with_controller.py` - Integration tests
- `tests/test_e2e_recording.py` - End-to-end tests

### Modified Files
- `src/whisper_app/gui.py` - Use CommandController instead of FIFO directly
- `tests/test_gui.py` - Update mocks and add new test cases

## Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/whisper_app --cov-report=html

# Run specific test category
pytest tests/test_ipc_controller.py -v

# Run integration tests only
pytest tests/test_gui_with_controller.py -v
```

## Success Criteria

- [ ] All existing tests pass
- [ ] New tests have >90% coverage
- [ ] Can create GUI with FIFO controller
- [ ] Can create GUI with D-Bus controller (stub)
- [ ] No changes to public API
- [ ] Command handling works identically with both controllers
- [ ] No performance regression
