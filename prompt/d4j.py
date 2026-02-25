
PURE_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version for each buggy function. Do not response anything else except the refined version of buggy function."""

DIFF_INSTRUCTION = """As an AI debugger, your duty is to generate a diff patch for each buggy function. Do not response anything else except the diff patch of buggy function.Ensure the generated patch uses the correct line numbers based on the line number annotation."""

LOCATED_INSTRUCTION = """As an AI debugger, your duty is to generate code snippets to fill the chunks marked as `<Chunk_For_Modification>` in each provided buggy function. Do not response anything else except the generated code snippets."""

SEARCH_REPLACE_INSTRUCTION_1 ="""We are currently solving the following issue within our repository. Here is the bug report:
### Buggy function comment:
{BUGGY_COMMENT}

### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit tests:
{FAILED_TEST}

### Buggy functions (You need to generate Search/Replace edit for each buggy function,Do not response anything else except Search/Replace edit.):
{BUGGY_CODE}
--- END FILE ---

Please first localize the bug based on the bug report, and then generate *SEARCH/REPLACE* edits to fix the issue.Finally, please apply the *SEARCH/REPLACE* edits to buggy function.

Every *SEARCH/REPLACE* edit must use this format:
1. function signature 
2. The start of search block: <<<<<<< SEARCH
3. A contiguous chunk of lines to search for in the existing source code
4. The dividing line: =======
5. The lines to replace into the source code
6. The end of the replace block: >>>>>>> REPLACE

Here is an example of *SEARCH/REPLACE* edit:
```java
###private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)
<<<<<<< SEARCH
    // Make label names unique to this instance.
=======
    // Make label names unique to this instance.
    new RenameLabels(compiler, new LabelNameSupplier(idSupplier), false)
        .process(null, fnNode);
>>>>>>> REPLACE
```
```java
###private void visitLabel(Node node,Node parent)
<<<<<<< SEARCH
      if (li.referenced) {
=======
      if (li.referenced || !removeUnused) {
>>>>>>> REPLACE
```

Please note that the *SEARCH/REPLACE* edit REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
After generating the *SEARCH/REPLACE* edit, please apply it to the buggy function and provide the fixed function.
Here is an example of providing the fixed function:
###FIXED FUNCTION
```java
private void visitLabel(Node node, Node parent) {
      Node nameNode = node.getFirstChild();
      Preconditions.checkState(nameNode != null);
      String name = nameNode.getString();
      LabelInfo li = getLabelInfo(name);
      // This is a label...
      if (li.referenced || !removeUnused) {
        String newName = getNameForId(li.id);
        if (!name.equals(newName)) {
          // ... and it is used, give it the short name.
          nameNode.setString(newName);
          compiler.reportCodeChange();
        }
      } else {
        // ... and it is not referenced, just remove it.
        Node newChild = node.getLastChild();
        node.removeChild(newChild);
        parent.replaceChild(node, newChild);
        if (newChild.getType() == Token.BLOCK) {
          NodeUtil.tryMergeBlock(newChild);
        }
        compiler.reportCodeChange();
      }

      // Remove the label from the current stack of labels.
      namespaceStack.peek().renameMap.remove(name);
    }
```
```java
  private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();
    // Make variable names unique to this instance.
    NodeTraversal.traverse(
        compiler, fnNode, new MakeDeclaredNamesUnique(
            new InlineRenamer(
                idSupplier,
                "inline_",
                isCallInLoop)));
    // Make label names unique to this instance.
    new RenameLabels(compiler, new LabelNameSupplier(idSupplier), false)
        .process(null, fnNode);
  }
```
"""
SR_EDIT_INSTRUCTION = """"As an AI debugger, your duty is to generate *SEARCH/REPLACE* edit for each buggy function. Do not response anything else except Search/Replace edit! 

Every *SEARCH/REPLACE* edit must use this format:
1. function signature (like `###private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)`)
2. The start of search block: <<<<<<< SEARCH
3. A contiguous chunk of lines to search for in the existing source code
4. The dividing line: =======
5. The lines to replace into the source code
6. The end of the replace block: >>>>>>> REPLACE

Please note that the *SEARCH/REPLACE* edit REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!"""
HYBRID_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version for each buggy function, where the buggy chunks are marked as `<Chunk_For_Modification>` in each provided buggy function. Do not response anything else except the refined version of buggy function."""

GENERAL_INSTRUCTION = """You are ChatGPT, a large language model trained by OpenAI.
Carefully heed the user's instructions.
Respond using Markdown.
Current Date: 2024/2/4 21:11:20"""

AGENT_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version of the buggy function for each bug report. Do not response anything else except the refined version of buggy function."""

AGENT_INSTRUCTION_MUTI="""As an AI debugger, your duty is to generate a refined version of the buggy functions for each buggy function in the bug report. Do not response anything else except the refined version of buggy functions and their file pathes."""

REVERSE_INSTRUCTION = """As an AI debugger, your duty is to generate the corrected code snippets for the buggy locations via referring the given bug report. Do not response anything else except the generated code snippets."""

MERGE_INSTRUCTION = """As an AI merger, your duty is to generate a merged program via applying the given patch to the given function. Do not response anything else except the merged function."""

USER_PROMPT = """
{BUGGY_CODE}
"""

GO_PROMPT = """```go
{BUGGY_CODE}
```"""


AGENT_PROMPT_MUTI= """### Buggy function comment:
{BUGGY_COMMENT}

### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit tests:
{FAILED_TEST}

### Buggy functions (You need to generate a fixed version of this program):
{BUGGY_CODE}
"""

AGENT_PROMPT_MUTI= """### Buggy function comment:
{BUGGY_COMMENT}

### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit tests:
{FAILED_TEST}

### Buggy functions (You need to generate a fixed version of this program):
{BUGGY_CODE}
"""

AGENT_PROMPT_MUTI_NO_COMMENT= """### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit tests:
{FAILED_TEST}

### Buggy functions (You need to generate a fixed version of this program):
{BUGGY_CODE}
"""

AGENT_PROMPT_MUTI_NO_TEST= """### Buggy function comment:
{BUGGY_COMMENT}

### Error message from JUnit test:
{ERROR_MESSAGE}

### Buggy functions (You need to generate a fixed version of this program):
{BUGGY_CODE}
"""

AGENT_PROMPT_MUTI_NO_MESSAGE= """### Buggy function comment:
{BUGGY_COMMENT}

### Failed JUnit tests:
{FAILED_TEST}

### Buggy functions (You need to generate a fixed version of this program):
{BUGGY_CODE}
"""


AGENT_PROMPT_SR= """### Buggy function comment:
{BUGGY_COMMENT}

### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit tests:
{FAILED_TEST}

### Buggy functions:(You need to generate a *SEARCH/REPLACE* edit for each buggy function)
{BUGGY_CODE}
"""

AGENT_PROMPT = """### Buggy function comment:
{BUGGY_COMMENT}

### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit test:
```java
{FAILED_TEST}
```

### Buggy function (You need to generate a fixed version of this program):
```java
{BUGGY_CODE}
```"""

AGENT_PROMPT_DIFF = """### Buggy function comment:
{BUGGY_COMMENT}

### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit test:
```java
{FAILED_TEST}
```

### Buggy function (You need to generate a diff patch of this program.first you should find the buggy lines of the buggy function,then generate a diff patch according to the buggy lines.Please ensure the generated patch uses the correct line numbers based on line number annotation):
{BUGGY_CODE}
"""

AGENT_PROMPT_SR_AIDER = """
Please fix bug according to the following bug report:
### Error message from JUnit test:
{ERROR_MESSAGE}

### Failed JUnit test:
```java
{FAILED_TEST}
```
### Buggy function:
{BUGGY_FUNC}
"""



ZERO_PROMPT = """{BUGGY_CODE}"""

NONE_INSTRUCTION = "\n\nDo not generate any natural language question, explanation, or description."

FREE_INSTRUCTION = "\n\nThis is a bug-free code snippet. Do not generate any natural language question, explanation, or description."

EXAMPLE_INPUT_FUNC_REFINE = """```java
public static double linearCombination(final double[] a, final double[] b)
        throws DimensionMismatchException {
        final int len = a.length;
        if (len != b.length) {
             throw new DimensionMismatchException(len, b.length);
         }
 
             // Revert to scalar multiplication.
 
         final double[] prodHigh = new double[len];
         double prodLowSum = 0;

        for (int i = 0; i < len; i++) {
            final double ai = a[i];
            final double ca = SPLIT_FACTOR * ai;
            final double aHigh = ca - (ca - ai);
            final double aLow = ai - aHigh;

            final double bi = b[i];
            final double cb = SPLIT_FACTOR * bi;
            final double bHigh = cb - (cb - bi);
            final double bLow = bi - bHigh;
            prodHigh[i] = ai * bi;
            final double prodLow = aLow * bLow - (((prodHigh[i] -
                                                    aHigh * bHigh) -
                                                   aLow * bHigh) -
                                                  aHigh * bLow);
            prodLowSum += prodLow;
        }

        // if(len == 1)
        // {
        //     return a[0]*b[0];
        // }
        final double prodHighCur = prodHigh[0];
        // double prodHighNext = len > 1 ? prodHigh[1] : 0;
        double prodHighNext = prodHigh[1];
        // if(len == 1)
        // {
        //     return prodHighCur;
        // }
        double sHighPrev = prodHighCur + prodHighNext;
        double sPrime = sHighPrev - prodHighNext;
        double sLowSum = (prodHighNext - (sHighPrev - sPrime)) + (prodHighCur - sPrime);

        final int lenMinusOne = len - 1;
        for (int i = 1; i < lenMinusOne; i++) {
            prodHighNext = prodHigh[i + 1];
            final double sHighCur = sHighPrev + prodHighNext;
            sPrime = sHighCur - prodHighNext;
            sLowSum += (prodHighNext - (sHighCur - sPrime)) + (sHighPrev - sPrime);
            sHighPrev = sHighCur;
        }

        double result = sHighPrev + (prodLowSum + sLowSum);

        if (Double.isNaN(result)) {
            // either we have split infinite numbers or some coefficients were NaNs,
            // just rely on the naive implementation and let IEEE754 handle this
            result = 0;
            for (int i = 0; i < len; ++i) {
                result += a[i] * b[i];
            }
        }

        return result;
    }
```"""

EXAMPLE_OUTPUT_FUNC_BASE = """```java
public static double linearCombination(final double[] a, final double[] b)
        throws DimensionMismatchException {
        final int len = a.length;
        if (len != b.length) {
             throw new DimensionMismatchException(len, b.length);
         }
 
         if (len == 1) {
             // Revert to scalar multiplication.
             return a[0] * b[0];
         }
 
         final double[] prodHigh = new double[len];
         double prodLowSum = 0;

        for (int i = 0; i < len; i++) {
            final double ai = a[i];
            final double ca = SPLIT_FACTOR * ai;
            final double aHigh = ca - (ca - ai);
            final double aLow = ai - aHigh;

            final double bi = b[i];
            final double cb = SPLIT_FACTOR * bi;
            final double bHigh = cb - (cb - bi);
            final double bLow = bi - bHigh;
            prodHigh[i] = ai * bi;
            final double prodLow = aLow * bLow - (((prodHigh[i] -
                                                    aHigh * bHigh) -
                                                   aLow * bHigh) -
                                                  aHigh * bLow);
            prodLowSum += prodLow;
        }

        // if(len == 1)
        // {
        //     return a[0]*b[0];
        // }
        final double prodHighCur = prodHigh[0];
        // double prodHighNext = len > 1 ? prodHigh[1] : 0;
        double prodHighNext = prodHigh[1];
        // if(len == 1)
        // {
        //     return prodHighCur;
        // }
        double sHighPrev = prodHighCur + prodHighNext;
        double sPrime = sHighPrev - prodHighNext;
        double sLowSum = (prodHighNext - (sHighPrev - sPrime)) + (prodHighCur - sPrime);

        final int lenMinusOne = len - 1;
        for (int i = 1; i < lenMinusOne; i++) {
            prodHighNext = prodHigh[i + 1];
            final double sHighCur = sHighPrev + prodHighNext;
            sPrime = sHighCur - prodHighNext;
            sLowSum += (prodHighNext - (sHighCur - sPrime)) + (sHighPrev - sPrime);
            sHighPrev = sHighCur;
        }

        double result = sHighPrev + (prodLowSum + sLowSum);

        if (Double.isNaN(result)) {
            // either we have split infinite numbers or some coefficients were NaNs,
            // just rely on the naive implementation and let IEEE754 handle this
            result = 0;
            for (int i = 0; i < len; ++i) {
                result += a[i] * b[i];
            }
        }

        return result;
    }
```"""



EXAMPLE_INPUT_FUNC_REPAIR = """public static double linearCombination(final double[] a, final double[] b)
        throws DimensionMismatchException {
        final int len = a.length;
        if (len != b.length) {
             throw new DimensionMismatchException(len, b.length);
         }
 
<Chunk_For_Modification>
             // Revert to scalar multiplication.
<Chunk_For_Modification>
 
         final double[] prodHigh = new double[len];
         double prodLowSum = 0;

        for (int i = 0; i < len; i++) {
            final double ai = a[i];
            final double ca = SPLIT_FACTOR * ai;
            final double aHigh = ca - (ca - ai);
            final double aLow = ai - aHigh;

            final double bi = b[i];
            final double cb = SPLIT_FACTOR * bi;
            final double bHigh = cb - (cb - bi);
            final double bLow = bi - bHigh;
            prodHigh[i] = ai * bi;
            final double prodLow = aLow * bLow - (((prodHigh[i] -
                                                    aHigh * bHigh) -
                                                   aLow * bHigh) -
                                                  aHigh * bLow);
            prodLowSum += prodLow;
        }

        // if(len == 1)
        // {
        //     return a[0]*b[0];
        // }
        final double prodHighCur = prodHigh[0];
        // double prodHighNext = len > 1 ? prodHigh[1] : 0;
        double prodHighNext = prodHigh[1];
        // if(len == 1)
        // {
        //     return prodHighCur;
        // }
        double sHighPrev = prodHighCur + prodHighNext;
        double sPrime = sHighPrev - prodHighNext;
        double sLowSum = (prodHighNext - (sHighPrev - sPrime)) + (prodHighCur - sPrime);

        final int lenMinusOne = len - 1;
        for (int i = 1; i < lenMinusOne; i++) {
            prodHighNext = prodHigh[i + 1];
            final double sHighCur = sHighPrev + prodHighNext;
            sPrime = sHighCur - prodHighNext;
            sLowSum += (prodHighNext - (sHighCur - sPrime)) + (sHighPrev - sPrime);
            sHighPrev = sHighCur;
        }

        double result = sHighPrev + (prodLowSum + sLowSum);

        if (Double.isNaN(result)) {
            // either we have split infinite numbers or some coefficients were NaNs,
            // just rely on the naive implementation and let IEEE754 handle this
            result = 0;
            for (int i = 0; i < len; ++i) {
                result += a[i] * b[i];
            }
        }

        return result;
    }"""

EXAMPLE_OUTPUT_FUNC_LOCATED = """```java
if (len == 1) {
```
```java
return a[0] * b[0];
}
```
"""

EXAMPLE_OUTPUT_FUNC_MUTI= """
```java
private void visitLabel(Node node, Node parent) {
      Node nameNode = node.getFirstChild();
      Preconditions.checkState(nameNode != null);
      String name = nameNode.getString();
      LabelInfo li = getLabelInfo(name);
      // This is a label...
      if (li.referenced || !removeUnused) {
        String newName = getNameForId(li.id);
        if (!name.equals(newName)) {
          // ... and it is used, give it the short name.
          nameNode.setString(newName);
          compiler.reportCodeChange();
        }
      } else {
        // ... and it is not referenced, just remove it.
        Node newChild = node.getLastChild();
        node.removeChild(newChild);
        parent.replaceChild(node, newChild);
        if (newChild.getType() == Token.BLOCK) {
          NodeUtil.tryMergeBlock(newChild);
        }
        compiler.reportCodeChange();
      }

      // Remove the label from the current stack of labels.
      namespaceStack.peek().renameMap.remove(name);
    }
```
```java
  private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();
    // Make variable names unique to this instance.
    NodeTraversal.traverse(
        compiler, fnNode, new MakeDeclaredNamesUnique(
            new InlineRenamer(
                idSupplier,
                "inline_",
                isCallInLoop)));
    // Make label names unique to this instance.
    new RenameLabels(compiler, new LabelNameSupplier(idSupplier), false)
        .process(null, fnNode);
  }
```
"""

EXAMPLE_OUTPUT_FUNC_DIFF= """
diff --git a/src/com/google/javascript/jscomp/FunctionToBlockMutator.java b/src/com/google/javascript/jscomp/FunctionToBlockMutator.java
index 3fee1a9..64764c0 100644
--- a/src/com/google/javascript/jscomp/FunctionToBlockMutator.java
+++ b/src/com/google/javascript/jscomp/FunctionToBlockMutator.java
@@ -149,8 +149,6 @@ class FunctionToBlockMutator {
                 "inline_",
                 isCallInLoop)));
     // Make label names unique to this instance.
+    new RenameLabels(compiler, new LabelNameSupplier(idSupplier), false)
+        .process(null, fnNode);
   }
 
   static class LabelNameSupplier implements Supplier<String> {
diff --git a/src/com/google/javascript/jscomp/RenameLabels.java b/src/com/google/javascript/jscomp/RenameLabels.java
index 28e52ee..a2f53cf 100644
--- a/src/com/google/javascript/jscomp/RenameLabels.java
+++ b/src/com/google/javascript/jscomp/RenameLabels.java
@@ -212,7 +212,7 @@ final class RenameLabels implements CompilerPass {
       String name = nameNode.getString();
       LabelInfo li = getLabelInfo(name);
       // This is a label...
+      if (li.referenced || !removeUnused) {
-      if (li.referenced) {
         String newName = getNameForId(li.id);
         if (!name.equals(newName)) {
           // ... and it is used, give it the short name.
"""

EXAMPLE_OUTPUT_FUNC_SR_EDIT= """
```java
###private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)
<<<<<<< SEARCH
    // Make label names unique to this instance.
=======
    // Make label names unique to this instance.
    new RenameLabels(compiler, new LabelNameSupplier(idSupplier), false)
        .process(null, fnNode);
>>>>>>> REPLACE
```
```java
###private void visitLabel(Node node, Node parent)
<<<<<<< SEARCH
      if (li.referenced) {
=======
      if (li.referenced || !removeUnused) {
>>>>>>> REPLACE
```
"""

EXAMPLE_INPUT_FUNC_AGENT_MUTI= """### Buggy function comments:
    /**
     * Rename or remove labels.
     * @param node  The label node.
     * @param parent The parent of the label node.
     */
    private void visitLabel(Node node,Node parent)

    /**
   * Fix-up all local names to be unique for this subtree.
   * @param fnNode A mutable instance of the function to be inlined.
   */
    private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)

### Error message from JUnit test:
junit.framework.AssertionFailedError: 
Expected: lab:JSCompiler_inline_label_0:4
Result: lab:lab:4
Node tree inequality:
Tree1:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: expected0] [synthetic: 1]
        LABEL 1 [sourcename: expected0]
            LABEL_NAME lab 1 [sourcename: expected0]
            BLOCK 1 [sourcename: expected0]
                BLOCK 1 [sourcename: expected0]
                    LABEL 1 [sourcename: expected0]
                        LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]
                        BLOCK 1 [sourcename: expected0]
                            EXPR_RESULT 1 [sourcename: expected0]
                                NUMBER 4.0 1 [sourcename: expected0]

Tree2:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: testcode] [synthetic: 1]
        LABEL 1 [sourcename: testcode]
            LABEL_NAME lab 1 [sourcename: testcode]
            BLOCK 1 [sourcename: testcode]
                BLOCK 1 [sourcename: testcode]
                    LABEL 1 [sourcename: testcode]
                        LABEL_NAME lab 1 [sourcename: testcode]
                        BLOCK 1 [sourcename: testcode]
                            EXPR_RESULT 1 [sourcename: testcode]
                                NUMBER 4.0 1 [sourcename: testcode]


Subtree1: LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]

Subtree2: LABEL_NAME lab 1 [sourcename: testcode]

### Failed JUnit test:
```java
public void testInlineFunctions31() {
    // Don't introduce a duplicate label in the same scope
    test(""function foo(){ lab:{4;} }"" +
        ""lab:{foo();}"",
        ""lab:{{JSCompiler_inline_label_0:{4}}}"");
  }
```
### Buggy functions (You need to generate a fixed version of this program): 
```java
private void visitLabel(Node node, Node parent) {
      Node nameNode = node.getFirstChild();
      Preconditions.checkState(nameNode != null);
      String name = nameNode.getString();
      LabelInfo li = getLabelInfo(name);
      // This is a label...
      if (li.referenced) {
        String newName = getNameForId(li.id);
        if (!name.equals(newName)) {
          // ... and it is used, give it the short name.
          nameNode.setString(newName);
          compiler.reportCodeChange();
        }
      } else {
        // ... and it is not referenced, just remove it.
        Node newChild = node.getLastChild();
        node.removeChild(newChild);
        parent.replaceChild(node, newChild);
        if (newChild.getType() == Token.BLOCK) {
          NodeUtil.tryMergeBlock(newChild);
        }
        compiler.reportCodeChange();
      }

      // Remove the label from the current stack of labels.
      namespaceStack.peek().renameMap.remove(name);
    }
```

```java
private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();
    // Make variable names unique to this instance.
    NodeTraversal.traverse(
        compiler, fnNode, new MakeDeclaredNamesUnique(
            new InlineRenamer(
                idSupplier,
                ""inline_"",
                isCallInLoop)));
    // Make label names unique to this instance.
  }
```
"""


EXAMPLE_INPUT_FUNC_AGENT_MUTI_NO_COMMENT= """### Error message from JUnit test:
junit.framework.AssertionFailedError: 
Expected: lab:JSCompiler_inline_label_0:4
Result: lab:lab:4
Node tree inequality:
Tree1:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: expected0] [synthetic: 1]
        LABEL 1 [sourcename: expected0]
            LABEL_NAME lab 1 [sourcename: expected0]
            BLOCK 1 [sourcename: expected0]
                BLOCK 1 [sourcename: expected0]
                    LABEL 1 [sourcename: expected0]
                        LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]
                        BLOCK 1 [sourcename: expected0]
                            EXPR_RESULT 1 [sourcename: expected0]
                                NUMBER 4.0 1 [sourcename: expected0]

Tree2:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: testcode] [synthetic: 1]
        LABEL 1 [sourcename: testcode]
            LABEL_NAME lab 1 [sourcename: testcode]
            BLOCK 1 [sourcename: testcode]
                BLOCK 1 [sourcename: testcode]
                    LABEL 1 [sourcename: testcode]
                        LABEL_NAME lab 1 [sourcename: testcode]
                        BLOCK 1 [sourcename: testcode]
                            EXPR_RESULT 1 [sourcename: testcode]
                                NUMBER 4.0 1 [sourcename: testcode]


Subtree1: LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]

Subtree2: LABEL_NAME lab 1 [sourcename: testcode]

### Failed JUnit test:
```java
public void testInlineFunctions31() {
    // Don't introduce a duplicate label in the same scope
    test(""function foo(){ lab:{4;} }"" +
        ""lab:{foo();}"",
        ""lab:{{JSCompiler_inline_label_0:{4}}}"");
  }
```
### Buggy functions (You need to generate a fixed version of this program): 
```java
private void visitLabel(Node node, Node parent) {
      Node nameNode = node.getFirstChild();
      Preconditions.checkState(nameNode != null);
      String name = nameNode.getString();
      LabelInfo li = getLabelInfo(name);
      // This is a label...
      if (li.referenced) {
        String newName = getNameForId(li.id);
        if (!name.equals(newName)) {
          // ... and it is used, give it the short name.
          nameNode.setString(newName);
          compiler.reportCodeChange();
        }
      } else {
        // ... and it is not referenced, just remove it.
        Node newChild = node.getLastChild();
        node.removeChild(newChild);
        parent.replaceChild(node, newChild);
        if (newChild.getType() == Token.BLOCK) {
          NodeUtil.tryMergeBlock(newChild);
        }
        compiler.reportCodeChange();
      }

      // Remove the label from the current stack of labels.
      namespaceStack.peek().renameMap.remove(name);
    }
```

```java
private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();
    // Make variable names unique to this instance.
    NodeTraversal.traverse(
        compiler, fnNode, new MakeDeclaredNamesUnique(
            new InlineRenamer(
                idSupplier,
                ""inline_"",
                isCallInLoop)));
    // Make label names unique to this instance.
  }
```
"""


EXAMPLE_INPUT_FUNC_AGENT_MUTI_NO_TEST= """### Buggy function comments:
    /**
     * Rename or remove labels.
     * @param node  The label node.
     * @param parent The parent of the label node.
     */
    private void visitLabel(Node node,Node parent)

    /**
   * Fix-up all local names to be unique for this subtree.
   * @param fnNode A mutable instance of the function to be inlined.
   */
    private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)

### Error message from JUnit test:
junit.framework.AssertionFailedError: 
Expected: lab:JSCompiler_inline_label_0:4
Result: lab:lab:4
Node tree inequality:
Tree1:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: expected0] [synthetic: 1]
        LABEL 1 [sourcename: expected0]
            LABEL_NAME lab 1 [sourcename: expected0]
            BLOCK 1 [sourcename: expected0]
                BLOCK 1 [sourcename: expected0]
                    LABEL 1 [sourcename: expected0]
                        LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]
                        BLOCK 1 [sourcename: expected0]
                            EXPR_RESULT 1 [sourcename: expected0]
                                NUMBER 4.0 1 [sourcename: expected0]

Tree2:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: testcode] [synthetic: 1]
        LABEL 1 [sourcename: testcode]
            LABEL_NAME lab 1 [sourcename: testcode]
            BLOCK 1 [sourcename: testcode]
                BLOCK 1 [sourcename: testcode]
                    LABEL 1 [sourcename: testcode]
                        LABEL_NAME lab 1 [sourcename: testcode]
                        BLOCK 1 [sourcename: testcode]
                            EXPR_RESULT 1 [sourcename: testcode]
                                NUMBER 4.0 1 [sourcename: testcode]


Subtree1: LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]

Subtree2: LABEL_NAME lab 1 [sourcename: testcode]

### Buggy functions (You need to generate a fixed version of this program): 
```java
private void visitLabel(Node node, Node parent) {
      Node nameNode = node.getFirstChild();
      Preconditions.checkState(nameNode != null);
      String name = nameNode.getString();
      LabelInfo li = getLabelInfo(name);
      // This is a label...
      if (li.referenced) {
        String newName = getNameForId(li.id);
        if (!name.equals(newName)) {
          // ... and it is used, give it the short name.
          nameNode.setString(newName);
          compiler.reportCodeChange();
        }
      } else {
        // ... and it is not referenced, just remove it.
        Node newChild = node.getLastChild();
        node.removeChild(newChild);
        parent.replaceChild(node, newChild);
        if (newChild.getType() == Token.BLOCK) {
          NodeUtil.tryMergeBlock(newChild);
        }
        compiler.reportCodeChange();
      }

      // Remove the label from the current stack of labels.
      namespaceStack.peek().renameMap.remove(name);
    }
```

```java
private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();
    // Make variable names unique to this instance.
    NodeTraversal.traverse(
        compiler, fnNode, new MakeDeclaredNamesUnique(
            new InlineRenamer(
                idSupplier,
                ""inline_"",
                isCallInLoop)));
    // Make label names unique to this instance.
  }
```
"""

EXAMPLE_INPUT_FUNC_AGENT_MUTI_NO_MESSAGE= """### Buggy function comments:
    /**
     * Rename or remove labels.
     * @param node  The label node.
     * @param parent The parent of the label node.
     */
    private void visitLabel(Node node,Node parent)

    /**
   * Fix-up all local names to be unique for this subtree.
   * @param fnNode A mutable instance of the function to be inlined.
   */
    private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)

### Failed JUnit test:
```java
public void testInlineFunctions31() {
    // Don't introduce a duplicate label in the same scope
    test(""function foo(){ lab:{4;} }"" +
        ""lab:{foo();}"",
        ""lab:{{JSCompiler_inline_label_0:{4}}}"");
  }
```
### Buggy functions (You need to generate a fixed version of this program): 
```java
private void visitLabel(Node node, Node parent) {
      Node nameNode = node.getFirstChild();
      Preconditions.checkState(nameNode != null);
      String name = nameNode.getString();
      LabelInfo li = getLabelInfo(name);
      // This is a label...
      if (li.referenced) {
        String newName = getNameForId(li.id);
        if (!name.equals(newName)) {
          // ... and it is used, give it the short name.
          nameNode.setString(newName);
          compiler.reportCodeChange();
        }
      } else {
        // ... and it is not referenced, just remove it.
        Node newChild = node.getLastChild();
        node.removeChild(newChild);
        parent.replaceChild(node, newChild);
        if (newChild.getType() == Token.BLOCK) {
          NodeUtil.tryMergeBlock(newChild);
        }
        compiler.reportCodeChange();
      }

      // Remove the label from the current stack of labels.
      namespaceStack.peek().renameMap.remove(name);
    }
```

```java
private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();
    // Make variable names unique to this instance.
    NodeTraversal.traverse(
        compiler, fnNode, new MakeDeclaredNamesUnique(
            new InlineRenamer(
                idSupplier,
                ""inline_"",
                isCallInLoop)));
    // Make label names unique to this instance.
  }
```
"""

EXAMPLE_INPUT_FUNC_AGENT_DIFF= """### Buggy function comments:
    /**
     * Rename or remove labels.
     * @param node  The label node.
     * @param parent The parent of the label node.
     */
    private void visitLabel(Node node,Node parent)

    /**
   * Fix-up all local names to be unique for this subtree.
   * @param fnNode A mutable instance of the function to be inlined.
   */
    private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)
### Error message from JUnit test:
junit.framework.AssertionFailedError: 
Expected: lab:JSCompiler_inline_label_0:4
Result: lab:lab:4
Node tree inequality:
Tree1:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: expected0] [synthetic: 1]
        LABEL 1 [sourcename: expected0]
            LABEL_NAME lab 1 [sourcename: expected0]
            BLOCK 1 [sourcename: expected0]
                BLOCK 1 [sourcename: expected0]
                    LABEL 1 [sourcename: expected0]
                        LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]
                        BLOCK 1 [sourcename: expected0]
                            EXPR_RESULT 1 [sourcename: expected0]
                                NUMBER 4.0 1 [sourcename: expected0]

Tree2:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: testcode] [synthetic: 1]
        LABEL 1 [sourcename: testcode]
            LABEL_NAME lab 1 [sourcename: testcode]
            BLOCK 1 [sourcename: testcode]
                BLOCK 1 [sourcename: testcode]
                    LABEL 1 [sourcename: testcode]
                        LABEL_NAME lab 1 [sourcename: testcode]
                        BLOCK 1 [sourcename: testcode]
                            EXPR_RESULT 1 [sourcename: testcode]
                                NUMBER 4.0 1 [sourcename: testcode]


Subtree1: LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]

Subtree2: LABEL_NAME lab 1 [sourcename: testcode]

### Failed JUnit test:
```java
public void testInlineFunctions31() {
    // Don't introduce a duplicate label in the same scope
    test(""function foo(){ lab:{4;} }"" +
        ""lab:{foo();}"",
        ""lab:{{JSCompiler_inline_label_0:{4}}}"");
  }
```
### Buggy functions (You need to generate a diff patch of this program.first you should find the buggy lines of the buggy function,then generate a diff patch according to the buggy lines.Please ensure the generated patch uses the correct line numbers based on the Buggy functions location.Please Please remove the line number information when outputting the patch.): 
/src/com/google/javascript/jscomp/FunctionToBlockMutator.java
```java
private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {  // Line 142
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();  // Line 143
    // Make variable names unique to this instance.  // Line 144
    NodeTraversal.traverse(  // Line 145
        compiler, fnNode, new MakeDeclaredNamesUnique(  // Line 146
            new InlineRenamer(  // Line 147
                idSupplier,  // Line 148
                ""inline_"",  // Line 149
                isCallInLoop)));  // Line 150
    // Make label names unique to this instance.  // Line 151
  }  // Line 152
```
/src/com/google/javascript/jscomp/RenameLabels.java
```java
private void visitLabel(Node node, Node parent) {  // Line 209
      Node nameNode = node.getFirstChild();  // Line 210
      Preconditions.checkState(nameNode != null);  // Line 211
      String name = nameNode.getString();  // Line 212
      LabelInfo li = getLabelInfo(name);  // Line 213
      // This is a label...  // Line 214
      if (li.referenced) {  // Line 215
        String newName = getNameForId(li.id);  // Line 216
        if (!name.equals(newName)) {  // Line 217
          // ... and it is used, give it the short name.  // Line 218
          nameNode.setString(newName);  // Line 219
          compiler.reportCodeChange();  // Line 220
        }  // Line 221
      } else {  // Line 222
        // ... and it is not referenced, just remove it.  // Line 223
        Node newChild = node.getLastChild();  // Line 224
        node.removeChild(newChild);  // Line 225
        parent.replaceChild(node, newChild);  // Line 226
        if (newChild.getType() == Token.BLOCK) {  // Line 227
          NodeUtil.tryMergeBlock(newChild);  // Line 228
        }  // Line 229
        compiler.reportCodeChange();  // Line 230
      }  // Line 231
  // Line 232
      // Remove the label from the current stack of labels.  // Line 233
      namespaceStack.peek().renameMap.remove(name);  // Line 234
    }  // Line 235
```
"""


EXAMPLE_INPUT_FUNC_AGENT_SR_EDIT= """### Buggy function comments:
    /**
     * Rename or remove labels.
     * @param node  The label node.
     * @param parent The parent of the label node.
     */
    private void visitLabel(Node node,Node parent)

    /**
   * Fix-up all local names to be unique for this subtree.
   * @param fnNode A mutable instance of the function to be inlined.
   */
    private void makeLocalNamesUnique(Node fnNode,boolean isCallInLoop)
### Error message from JUnit test:
junit.framework.AssertionFailedError: 
Expected: lab:JSCompiler_inline_label_0:4
Result: lab:lab:4
Node tree inequality:
Tree1:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: expected0] [synthetic: 1]
        LABEL 1 [sourcename: expected0]
            LABEL_NAME lab 1 [sourcename: expected0]
            BLOCK 1 [sourcename: expected0]
                BLOCK 1 [sourcename: expected0]
                    LABEL 1 [sourcename: expected0]
                        LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]
                        BLOCK 1 [sourcename: expected0]
                            EXPR_RESULT 1 [sourcename: expected0]
                                NUMBER 4.0 1 [sourcename: expected0]

Tree2:
BLOCK [synthetic: 1]
    SCRIPT 1 [sourcename: testcode] [synthetic: 1]
        LABEL 1 [sourcename: testcode]
            LABEL_NAME lab 1 [sourcename: testcode]
            BLOCK 1 [sourcename: testcode]
                BLOCK 1 [sourcename: testcode]
                    LABEL 1 [sourcename: testcode]
                        LABEL_NAME lab 1 [sourcename: testcode]
                        BLOCK 1 [sourcename: testcode]
                            EXPR_RESULT 1 [sourcename: testcode]
                                NUMBER 4.0 1 [sourcename: testcode]


Subtree1: LABEL_NAME JSCompiler_inline_label_0 1 [sourcename: expected0]

Subtree2: LABEL_NAME lab 1 [sourcename: testcode]

### Failed JUnit test:
```java
public void testInlineFunctions31() {
    // Don't introduce a duplicate label in the same scope
    test(""function foo(){ lab:{4;} }"" +
        ""lab:{foo();}"",
        ""lab:{{JSCompiler_inline_label_0:{4}}}"");
  }
```
### Buggy functions ((You need to generate Search/Replace edit for each buggy function,Do not response anything else except Search/Replace edit.)): 
```java
private void makeLocalNamesUnique(Node fnNode, boolean isCallInLoop) {
    Supplier<String> idSupplier = compiler.getUniqueNameIdSupplier();
    // Make variable names unique to this instance.
    NodeTraversal.traverse(
        compiler, fnNode, new MakeDeclaredNamesUnique(
            new InlineRenamer(
                idSupplier,
                ""inline_"",
                isCallInLoop)));
    // Make label names unique to this instance.
  }
```
```java
private void visitLabel(Node node, Node parent) {
      Node nameNode = node.getFirstChild();
      Preconditions.checkState(nameNode != null);
      String name = nameNode.getString();
      LabelInfo li = getLabelInfo(name);
      // This is a label...
      if (li.referenced) {
        String newName = getNameForId(li.id);
        if (!name.equals(newName)) {
          // ... and it is used, give it the short name.
          nameNode.setString(newName);
          compiler.reportCodeChange();
        }
      } else {
        // ... and it is not referenced, just remove it.
        Node newChild = node.getLastChild();
        node.removeChild(newChild);
        parent.replaceChild(node, newChild);
        if (newChild.getType() == Token.BLOCK) {
          NodeUtil.tryMergeBlock(newChild);
        }
        compiler.reportCodeChange();
      }

      // Remove the label from the current stack of labels.
      namespaceStack.peek().renameMap.remove(name);
    }
```
"""


EXAMPLE_INPUT_FUNC_AGENT = """### Buggy function comment:
    /**
     * Compute a linear combination accurately.
     * This method computes the sum of the products
     * <code>a<sub>i</sub> b<sub>i</sub></code> to high accuracy.
     * It does so by using specific multiplication and addition algorithms to
     * preserve accuracy and reduce cancellation effects.
     * <br/>
     * It is based on the 2005 paper
     * <a href="http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.2.1547">
     * Accurate Sum and Dot Product</a> by Takeshi Ogita, Siegfried M. Rump,
     * and Shin'ichi Oishi published in SIAM J. Sci. Comput.
     *
     * @param a Factors.
     * @param b Factors.
     * @return <code>&Sigma;<sub>i</sub> a<sub>i</sub> b<sub>i</sub></code>.
     * @throws DimensionMismatchException if arrays dimensions don't match
     */

### Error message from JUnit test:
java.lang.ArrayIndexOutOfBoundsException: 1

### Failed JUnit test:
```java
    public void testLinearCombinationWithSingleElementArray() {
        final double[] a = { 1.23456789 };
        final double[] b = { 98765432.1 };

        Assert.assertEquals(a[0] * b[0], MathArrays.linearCombination(a, b), 0d);
    }
```

### Buggy function (You need to generate a fixed version of this program):
```java
public static double linearCombination(final double[] a, final double[] b) // **THIS IS LINE#0!**
        throws DimensionMismatchException {
        final int len = a.length;
        if (len != b.length) {
            throw new DimensionMismatchException(len, b.length);
        }

            // Revert to scalar multiplication.

        final double[] prodHigh = new double[len];
        double prodLowSum = 0;

        for (int i = 0; i < len; i++) {
            final double ai = a[i];
            final double ca = SPLIT_FACTOR * ai;
            final double aHigh = ca - (ca - ai);
            final double aLow = ai - aHigh;

            final double bi = b[i];
            final double cb = SPLIT_FACTOR * bi;
            final double bHigh = cb - (cb - bi);
            final double bLow = bi - bHigh;
            prodHigh[i] = ai * bi;
            final double prodLow = aLow * bLow - (((prodHigh[i] -
                                                    aHigh * bHigh) -
                                                   aLow * bHigh) -
                                                  aHigh * bLow);
            prodLowSum += prodLow;
        }


        final double prodHighCur = prodHigh[0];
        double prodHighNext = prodHigh[1];
        double sHighPrev = prodHighCur + prodHighNext;
        double sPrime = sHighPrev - prodHighNext;
        double sLowSum = (prodHighNext - (sHighPrev - sPrime)) + (prodHighCur - sPrime);

        final int lenMinusOne = len - 1;
        for (int i = 1; i < lenMinusOne; i++) {
            prodHighNext = prodHigh[i + 1];
            final double sHighCur = sHighPrev + prodHighNext;
            sPrime = sHighCur - prodHighNext;
            sLowSum += (prodHighNext - (sHighCur - sPrime)) + (sHighPrev - sPrime);
            sHighPrev = sHighCur;
        }

        double result = sHighPrev + (prodLowSum + sLowSum);

        if (Double.isNaN(result)) {
            // either we have split infinite numbers or some coefficients were NaNs,
            // just rely on the naive implementation and let IEEE754 handle this
            result = 0;
            for (int i = 0; i < len; ++i) {
                result += a[i] * b[i];
            }
        }

        return result;
    }
```"""


HISTORY_PURE_D4J = [
        {
            "role": "system",
            "content": PURE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_FUNC_REFINE
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_FUNC_BASE
        },
]


HISTORY_LOCATED_D4J = [
        {
            "role": "system",
            "content": LOCATED_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_FUNC_REPAIR
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_FUNC_LOCATED
        }
]

HISTORY_HYBRID_D4J = [
    {
        "role": "system",
        "content": HYBRID_INSTRUCTION
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_REPAIR
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_BASE
    }
]


HISTORY_GENERAL = [
    {
            "role": "system",
            "content": GENERAL_INSTRUCTION
    }
]

HISTORY_AGENT_D4J = [
    {
        "role": "system",
        "content": AGENT_INSTRUCTION
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_AGENT
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_BASE
    }
]


HISTORY_REVERSE_D4J = [
    {
        "role": "system",
        "content": REVERSE_INSTRUCTION
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_REPAIR
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_LOCATED
    }
]


HISTORY_AGENT_D4J_MUTI = [
    {
        "role": "system",
        "content": AGENT_INSTRUCTION_MUTI
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_AGENT_MUTI
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_MUTI
    }
]

HISTORY_AGENT_D4J_MUTI_NO_COMMENT = [
    {
        "role": "system",
        "content": AGENT_INSTRUCTION_MUTI
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_AGENT_MUTI_NO_COMMENT
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_MUTI
    }
]


HISTORY_AGENT_D4J_MUTI_NO_TEST = [
    {
        "role": "system",
        "content": AGENT_INSTRUCTION_MUTI
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_AGENT_MUTI_NO_TEST
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_MUTI
    }
]

HISTORY_AGENT_D4J_MUTI_NO_MESSAGE = [
    {
        "role": "system",
        "content": AGENT_INSTRUCTION_MUTI
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_AGENT_MUTI_NO_MESSAGE
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_MUTI
    }
]

HISTORY_AGENT_D4J_DIFF= [
    {
        "role": "system",
        "content": DIFF_INSTRUCTION
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_AGENT_DIFF
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_DIFF
    }
]

HISTORY_AGENT_D4J_SEARCH_REPLACE=[
    {
        "role": "system",
        "content": SR_EDIT_INSTRUCTION
    },
    {
        "role": "user",
        "content": EXAMPLE_INPUT_FUNC_AGENT_SR_EDIT
    },
    {
        "role": "assistant",
        "content": EXAMPLE_OUTPUT_FUNC_SR_EDIT
    }
]
