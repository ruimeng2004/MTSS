---
inclusion: always
---

# Coding Standards and Documentation Rules

## Documentation Policy

**Do NOT create documentation unless explicitly requested by the user.**

- ❌ Do not write summary documents after completing tasks
- ❌ Do not create README files to document your work
- ❌ Do not generate reports or analysis documents
- ❌ Do not create markdown files explaining what you did
- ✅ Only create documentation when the user specifically asks for it

**Exception**: Technical documentation that is part of the code (docstrings, inline comments) is always required.

## Code Style: Google Style Guide

All code must follow Google Style Guide conventions:

### Python (Google Python Style Guide)

```python
def calculate_statistics(data: List[float], 
                         threshold: float = 0.5) -> Dict[str, float]:
    """Calculate basic statistics for the given data.
    
    Args:
        data: List of numerical values to analyze.
        threshold: Minimum value to include in calculations. Defaults to 0.5.
    
    Returns:
        Dictionary containing 'mean', 'median', and 'std' keys.
    
    Raises:
        ValueError: If data is empty or contains non-numeric values.
    """
    if not data:
        raise ValueError("Data cannot be empty")
    
    filtered_data = [x for x in data if x >= threshold]
    return {
        'mean': statistics.mean(filtered_data),
        'median': statistics.median(filtered_data),
        'std': statistics.stdev(filtered_data)
    }
```

**Key Points**:
- Use 4 spaces for indentation
- Maximum line length: 80 characters (100 for docstrings/comments)
- Use docstrings for all public functions, classes, and modules
- Type hints for function parameters and return values
- Snake_case for functions and variables
- PascalCase for classes
- UPPER_CASE for constants

### JavaScript/TypeScript (Google JavaScript Style Guide)

```javascript
/**
 * Processes user data and returns formatted results.
 * @param {Object} userData - The user data object.
 * @param {string} userData.name - User's name.
 * @param {number} userData.age - User's age.
 * @return {string} Formatted user information.
 */
function processUserData(userData) {
  const {name, age} = userData;
  return `${name} (${age} years old)`;
}
```

**Key Points**:
- Use 2 spaces for indentation
- Use const/let, never var
- camelCase for functions and variables
- PascalCase for classes
- JSDoc comments for all functions

### Java (Google Java Style Guide)

```java
/**
 * Calculates the factorial of a number.
 *
 * @param n the number to calculate factorial for
 * @return the factorial of n
 * @throws IllegalArgumentException if n is negative
 */
public long factorial(int n) {
  if (n < 0) {
    throw new IllegalArgumentException("n must be non-negative");
  }
  
  long result = 1;
  for (int i = 2; i <= n; i++) {
    result *= i;
  }
  return result;
}
```

**Key Points**:
- Use 2 spaces for indentation
- Opening brace on same line
- Javadoc for all public methods
- camelCase for methods and variables
- PascalCase for classes

## Professional Code Standards

### 1. Clear and Descriptive Names
```python
# ❌ Bad
def calc(d, t):
    return sum([x for x in d if x > t])

# ✅ Good
def calculate_filtered_sum(data: List[float], threshold: float) -> float:
    """Calculate sum of values above threshold."""
    return sum(value for value in data if value > threshold)
```

### 2. Single Responsibility
```python
# ❌ Bad - does too many things
def process_data(data):
    # Load data
    # Clean data
    # Analyze data
    # Save results
    pass

# ✅ Good - separate concerns
def load_data(filepath: str) -> pd.DataFrame:
    """Load data from file."""
    pass

def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    """Remove invalid entries and normalize."""
    pass

def analyze_data(data: pd.DataFrame) -> Dict[str, Any]:
    """Perform statistical analysis."""
    pass
```

### 3. Error Handling
```python
# ✅ Good - explicit error handling
def read_config(filepath: str) -> Dict[str, Any]:
    """Read configuration from JSON file.
    
    Args:
        filepath: Path to configuration file.
    
    Returns:
        Configuration dictionary.
    
    Raises:
        FileNotFoundError: If config file doesn't exist.
        json.JSONDecodeError: If config file is invalid JSON.
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {filepath}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in config file: {filepath}", 
            e.doc, 
            e.pos
        )
```

### 4. Type Safety
```python
# ✅ Good - use type hints
from typing import List, Dict, Optional, Union

def process_items(
    items: List[str],
    config: Dict[str, Any],
    max_count: Optional[int] = None
) -> Union[List[str], None]:
    """Process items according to configuration."""
    pass
```

### 5. Avoid Magic Numbers
```python
# ❌ Bad
if score > 0.75:
    return "pass"

# ✅ Good
PASSING_THRESHOLD = 0.75

if score > PASSING_THRESHOLD:
    return "pass"
```

### 6. DRY (Don't Repeat Yourself)
```python
# ❌ Bad - repeated logic
def process_user_data(data):
    if not data or len(data) == 0:
        raise ValueError("Empty data")
    # process...

def process_product_data(data):
    if not data or len(data) == 0:
        raise ValueError("Empty data")
    # process...

# ✅ Good - extract common logic
def validate_data(data: Any, name: str) -> None:
    """Validate that data is not empty."""
    if not data or len(data) == 0:
        raise ValueError(f"Empty {name} data")

def process_user_data(data):
    validate_data(data, "user")
    # process...

def process_product_data(data):
    validate_data(data, "product")
    # process...
```

## Code Review Checklist

Before submitting code, ensure:

- [ ] Follows Google Style Guide for the language
- [ ] All functions have docstrings/comments
- [ ] Type hints are used (Python)
- [ ] No magic numbers or strings
- [ ] Error handling is explicit
- [ ] Variable names are descriptive
- [ ] Functions have single responsibility
- [ ] No code duplication
- [ ] No unnecessary documentation files created

## References

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html)
- [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
