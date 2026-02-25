PURE_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version for each buggy function. Do not response anything else except the refined version of buggy function."""

LOCATED_INSTRUCTION = """As an AI debugger, your duty is to generate code snippets to fill the chunks marked as `<Chunk_For_Modification>` in each provided buggy function. Do not response anything else except the generated code snippets."""

HYBRID_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version for each buggy function, where the buggy chunks are marked as `<Chunk_For_Modification>` in each provided buggy function. Do not response anything else except the refined version of buggy function."""

AGENT_INSTRUCTION = """As an AI debugger, your duty is to generate a refined version of the buggy function for each bug report. Do not response anything else except the refined version of buggy function."""

REVERSE_INSTRUCTION = """As an AI debugger, your duty is to generate the corrected code snippets for the buggy locations via referring the given bug report. Do not response anything else except the generated code snippets."""

MERGE_INSTRUCTION = """As an AI merger, your duty is to generate a merged program via applying the given patch to the given function. Do not response anything else except the merged function."""




USER_PROMPT = """```{LANGUAGE}
{BUGGY_CODE}
```"""




AGENT_PROMPT = """### Program requirements:
```
{REQUIREMENT}
```

### Input constraints:
```
{CONSTRAINT}
```

### Test examples:
```
{EXAMPLE}
```

### Buggy program:
```{LANGUAGE}
{BUGGY_CODE}
```"""




MERGE_PROMPT = """### Patch:
```{LANGUAGE}
{PATCH}
```

### Function:
```{LANGUAGE}
{SOURCE}
```"""



ZERO_PROMPT = """{BUGGY_CODE}"""

NONE_INSTRUCTION = "\n\nDo not generate any natural language question, explanation, or description."

FREE_INSTRUCTION = "\n\nThis is a bug-free code snippet. Do not generate any natural language question, explanation, or description."





EXAMPLE_INPUT_CPP_REFINE = """```cpp
class Solution {
public:

vector<int> countsort(vector<int> &nums)
{
    int n = nums.size();
    map<int, int> m;
    for (int i = 0; i < n; i++ )
        m[nums[i]]++;

    nums.clear();
    for (auto it : m)
    {
        int cnt = it.second;
        while (cnt--)
        {
            nums.push_back(it.first);
        }
    }
    return nums;
}

int maximumGap(vector<int> &nums)
{
    int n = nums.size();
    if (n < 2)
        return 0;
    vector<int> sortednums = countsort(nums);

    int maxgap = INT_MIN;
    for (int i = 1; i <= n; i++)
    {
        int currgap = sortednums[i] - sortednums[i - 1];
        maxgap = max(maxgap, currgap);
    }

    return maxgap;
}
};
```"""






EXAMPLE_INPUT_CPP_REPORT = """### Program requirements:
```
Given an integer array nums, return the maximum difference between two successive elements in its sorted form. If the array contains less than two elements, return 0.
You must write an algorithm that runs in linear time and uses linear extra space.
```

### Input constraints:
```
1 <= nums.length <= 105
0 <= nums[i] <= 109
```

### Test examples:
```
Input: nums = [3,6,9,1]
Output: 3
Explanation: The sorted form of the array is [1,3,6,9], either (3,6) or (6,9) has the maximum difference 3.
Input: nums = [10]
Output: 0
Explanation: The array contains less than 2 elements, therefore return 0.
```

### Buggy program:
```cpp
class Solution {
public:

vector<int> countsort(vector<int> &nums)
{
    int n = nums.size();
    map<int, int> m;
    for (int i = 0; i < n; i++ )
        m[nums[i]]++;

    nums.clear();
    for (auto it : m)
    {
        int cnt = it.second;
        while (cnt--)
        {
            nums.push_back(it.first);
        }
    }
    return nums;
}

int maximumGap(vector<int> &nums)
{
    int n = nums.size();
    if (n < 2)
        return 0;
    vector<int> sortednums = countsort(nums);

    int maxgap = INT_MIN;
    for (int i = 1; i <= n; i++)
    {
        int currgap = sortednums[i] - sortednums[i - 1];
        maxgap = max(maxgap, currgap);
    }

    return maxgap;
}
};
```"""



















EXAMPLE_INPUT_CPP_MASK = """```cpp
class Solution {
public:

vector<int> countsort(vector<int> &nums)
{
    int n = nums.size();
    map<int, int> m;
    for (int i = 0; i < n; i++ )
        m[nums[i]]++;

    nums.clear();
    for (auto it : m)
    {
        int cnt = it.second;
        while (cnt--)
        {
            nums.push_back(it.first);
        }
    }
    return nums;
}

int maximumGap(vector<int> &nums)
{
    int n = nums.size();
    if (n < 2)
        return 0;
    vector<int> sortednums = countsort(nums);

    int maxgap = INT_MIN;
<Chunk_For_Modification>
    {
        int currgap = sortednums[i] - sortednums[i - 1];
        maxgap = max(maxgap, currgap);
    }

    return maxgap;
}
};
```"""
















EXAMPLE_OUTPUT_CPP_FUNC = """```cpp
class Solution {
public:

vector<int> countsort(vector<int> &nums)
{
    int n = nums.size();
    map<int, int> m;
    for (int i = 0; i < n; i++ )
        m[nums[i]]++;

    nums.clear();
    for (auto it : m)
    {
        int cnt = it.second;
        while (cnt--)
        {
            nums.push_back(it.first);
        }
    }
    return nums;
}

int maximumGap(vector<int> &nums)
{
    int n = nums.size();
    if (n < 2)
        return 0;
    vector<int> sortednums = countsort(nums);

    int maxgap = INT_MIN;
    for (int i = 1; i < n; i++)
    {
        int currgap = sortednums[i] - sortednums[i - 1];
        maxgap = max(maxgap, currgap);
    }

    return maxgap;
}
};
```"""













EXAMPLE_OUTPUT_CPP_HUNK = """```cpp
    for (int i = 1; i < n; i++)
```"""













EXAMPLE_INPUT_JAVA_REFINE = """```java
class Solution {
    public String[] findRelativeRanks(int[] score) {
         int n=score.length;
        PriorityQueue<Integer> pq=new PriorityQueue<>((a,b)-> score[b]-score[a]);
        for(int i=0;i<n;i++) pq.add(i);
        String[] ans = null;
        int i=1;
        while(!pq.isEmpty()){
            int idx=pq.poll();
            if(i=1) { ans[idx]="Gold Medal"; i++;} 
            else if(i=2) { ans[idx]="Silver Medal"; i++;} 
            else if(i=3) { ans[idx]="Bronze Medal"; i++;} 
            else ans[idx]=Integer.toString(i++);
        }
        return reorderArray(ans);  
    }

    private String[] reorderArray(String[] ranks){
        
    }
}
```"""








EXAMPLE_INPUT_JAVA_REPORT = """### Program requirements:
```
You are given an integer array score of size n, where score[i] is the score of the ith athlete in a competition. All the scores are guaranteed to be unique.
The athletes are placed based on their scores, where the 1st place athlete has the highest score, the 2nd place athlete has the 2nd highest score, and so on. The placement of each athlete determines their rank:

The 1st place athlete's rank is "Gold Medal".
The 2nd place athlete's rank is "Silver Medal".
The 3rd place athlete's rank is "Bronze Medal".
For the 4th place to the nth place athlete, their rank is their placement number (i.e., the xth place athlete's rank is "x").

Return an array answer of size n where answer[i] is the rank of the ith athlete.
```

### Input constraints:
```
n == score.length
1 <= n <= 104
0 <= score[i] <= 106
All the values in score are unique.
```

### Test examples:
```
Input: score = [5,4,3,2,1]
Output: ["Gold Medal","Silver Medal","Bronze Medal","4","5"]
Explanation: The placements are [1st, 2nd, 3rd, 4th, 5th].
Input: score = [10,3,8,9,4]
Output: ["Gold Medal","5","Bronze Medal","Silver Medal","4"]
Explanation: The placements are [1st, 5th, 3rd, 2nd, 4th].
```

### Buggy program:
```java
class Solution {
    public String[] findRelativeRanks(int[] score) {
         int n=score.length;
        PriorityQueue<Integer> pq=new PriorityQueue<>((a,b)-> score[b]-score[a]);
        for(int i=0;i<n;i++) pq.add(i);
        String[] ans = null;
        int i=1;
        while(!pq.isEmpty()){
            int idx=pq.poll();
            if(i=1) { ans[idx]="Gold Medal"; i++;} 
            else if(i=2) { ans[idx]="Silver Medal"; i++;} 
            else if(i=3) { ans[idx]="Bronze Medal"; i++;} 
            else ans[idx]=Integer.toString(i++);
        }
        return reorderArray(ans);  
    }

    private String[] reorderArray(String[] ranks){
        
    }
}
```"""












EXAMPLE_INPUT_JAVA_MASK = """```java
class Solution {
    public String[] findRelativeRanks(int[] score) {
         int n=score.length;
        PriorityQueue<Integer> pq=new PriorityQueue<>((a,b)-> score[b]-score[a]);
        for(int i=0;i<n;i++) pq.add(i);
<Chunk_For_Modification>
        int i=1;
        while(!pq.isEmpty()){
            int idx=pq.poll();
            if(i=1) { ans[idx]="Gold Medal"; i++;} 
            else if(i=2) { ans[idx]="Silver Medal"; i++;} 
            else if(i=3) { ans[idx]="Bronze Medal"; i++;} 
            else ans[idx]=Integer.toString(i++);
        }
        return reorderArray(ans);  
    }

<Chunk_For_Modification>
}
```"""













EXAMPLE_OUTPUT_JAVA_FUNC = """```java
class Solution {
    public String[] findRelativeRanks(int[] score) {
         int n=score.length;
        PriorityQueue<Integer> pq=new PriorityQueue<>((a,b)-> score[b]-score[a]);
        for(int i=0;i<n;i++) pq.add(i);
        String[] ans = new String[n];
        int i=1;
        while(!pq.isEmpty()){
            int idx=pq.poll();
            if(i=1) { ans[idx]="Gold Medal"; i++;} 
            else if(i=2) { ans[idx]="Silver Medal"; i++;} 
            else if(i=3) { ans[idx]="Bronze Medal"; i++;} 
            else ans[idx]=Integer.toString(i++);
        }
        return reorderArray(ans);  
    }
}
```"""












EXAMPLE_OUTPUT_JAVA_HUNK = """```java
        String[] ans = new String[n];
```
```java
```"""












EXAMPLE_INPUT_PYTHON_REFINE = """```python3
class Solution:
    def addBinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = carry >> 1
        return res[::-1][1]  

    def addNegabinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = -(carry >> 1)
        while len(res) > 1 and res[-1] == 0:
            res.pop()
        return res[::-1][1]
```"""

















EXAMPLE_INPUT_PYTHON_REPORT = """### Program requirements:
```
Given two numbers arr1 and arr2 in base -2, return the result of adding them together.
Each number is given in array format: as an array of 0s and 1s, from most significant bit to least significant bit. For example, arr = [1,1,0,1] represents the number (-2)^3+ (-2)^2 + (-2)^0 = -3. A number arr in array, format is also guaranteed to have no leading zeros: eitherarr == [0] or arr[0] == 1.
Return the result of adding arr1 and arr2 in the same format: as an array of 0s and 1s with no leading zeros.",
```

### Input constraints:
```
1 <= arr1.length, arr2.length <= 1000
arr1[i] and arr2[i] are 0 or 1
arr1 and arr2 have no leading zeros
```

### Test examples:
```
Input: arr1 = [1,1,1,1,1], arr2 = [1,0,1]
Output: [1,0,0,0,0]
Explanation: arr1 represents 11, arr2 represents 5, the output represents 16.
Input: arr1 = [0], arr2 = [0]
Output: [0]
Input: arr1 = [0], arr2 = [1]
Output: [1]
```

### Buggy program:
```python3
class Solution:
    def addBinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = carry >> 1
        return res[::-1][1]  

    def addNegabinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = -(carry >> 1)
        while len(res) > 1 and res[-1] == 0:
            res.pop()
        return res[::-1][1]
```"""













EXAMPLE_INPUT_PYTHON_MASK = """```python3
class Solution:
    def addBinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = carry >> 1
<Chunk_For_Modification>  

    def addNegabinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = -(carry >> 1)
        while len(res) > 1 and res[-1] == 0:
            res.pop()
<Chunk_For_Modification>
```"""











EXAMPLE_OUTPUT_PYTHON_FUNC = """```python3
class Solution:
    def addBinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = carry >> 1
        return res[::-1]

    def addNegabinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = -(carry >> 1)
        while len(res) > 1 and res[-1] == 0:
            res.pop()
        return res[::-1]
```"""











EXAMPLE_OUTPUT_PYTHON_HUNK = """```python3
        return res[::-1]
```python3
        return res[::-1]
```"""

















EXAMPLE_INPUT_MERGE_CPP = """### Patch:
```cpp
    for (int i = 1; i < n; i++)
```

### Function:
```cpp
class Solution {
public:

vector<int> countsort(vector<int> &nums)
{
    int n = nums.size();
    map<int, int> m;
    for (int i = 0; i < n; i++ )
        m[nums[i]]++;

    nums.clear();
    for (auto it : m)
    {
        int cnt = it.second;
        while (cnt--)
        {
            nums.push_back(it.first);
        }
    }
    return nums;
}

int maximumGap(vector<int> &nums)
{
    int n = nums.size();
    if (n < 2)
        return 0;
    vector<int> sortednums = countsort(nums);

    int maxgap = INT_MIN;
    for (int i = 1; i <= n; i++)
    {
        int currgap = sortednums[i] - sortednums[i - 1];
        maxgap = max(maxgap, currgap);
    }

    return maxgap;
}
};
```"""















EXAMPLE_INPUT_MERGE_JAVA = """### Patch:
```java
        String[] ans = new String[n];
```
```java
```

### Function:
```java
class Solution {
    public String[] findRelativeRanks(int[] score) {
         int n=score.length;
        PriorityQueue<Integer> pq=new PriorityQueue<>((a,b)-> score[b]-score[a]);
        for(int i=0;i<n;i++) pq.add(i);
        String[] ans = null;
        int i=1;
        while(!pq.isEmpty()){
            int idx=pq.poll();
            if(i=1) { ans[idx]="Gold Medal"; i++;} 
            else if(i=2) { ans[idx]="Silver Medal"; i++;} 
            else if(i=3) { ans[idx]="Bronze Medal"; i++;} 
            else ans[idx]=Integer.toString(i++);
        }
        return reorderArray(ans);  
    }

    private String[] reorderArray(String[] ranks){
        
    }
}
```"""




EXAMPLE_INPUT_MERGE_PYTHON = """### Patch:
```python3
        return res[::-1]
```python3
        return res[::-1]
```

```python3
class Solution:
    def addBinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = carry >> 1
        return res[::-1][1]  

    def addNegabinary(self, A, B):
        res = []
        carry = 0
        while A or B or carry:
            carry += (A or [0]).pop() + (B or [0]).pop()
            res.append(carry & 1)
            carry = -(carry >> 1)
        while len(res) > 1 and res[-1] == 0:
            res.pop()
        return res[::-1][1]
```"""




HISTORY_AGENT_CPP = [
        {
            "role": "system",
            "content": AGENT_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_CPP_REPORT
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_CPP_FUNC
        }
]








HISTORY_LOCATED_CPP = [
        {
            "role": "system",
            "content": LOCATED_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_CPP_MASK
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_CPP_HUNK
        }
]









HISTORY_HYBRID_CPP = [
        {
            "role": "system",
            "content": HYBRID_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_CPP_MASK
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_CPP_FUNC
        }
]











HISTORY_REVERSE_CPP = [
        {
            "role": "system",
            "content": REVERSE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_CPP_REPORT
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_CPP_HUNK
        }
]









HISTORY_PURE_CPP = [
        {
            "role": "system",
            "content": PURE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_CPP_REFINE
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_CPP_FUNC
        },
]









HISTORY_AGENT_JAVA = [
        {
            "role": "system",
            "content": AGENT_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_JAVA_REPORT
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_JAVA_FUNC
        }
]







HISTORY_LOCATED_JAVA = [
        {
            "role": "system",
            "content": LOCATED_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_JAVA_MASK
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_JAVA_HUNK
        }
]






HISTORY_HYBRID_JAVA = [
        {
            "role": "system",
            "content": HYBRID_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_JAVA_MASK
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_JAVA_FUNC
        }
]








HISTORY_REVERSE_JAVA = [
        {
            "role": "system",
            "content": REVERSE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_JAVA_REPORT
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_JAVA_HUNK
        }
]






HISTORY_PURE_JAVA = [
        {
            "role": "system",
            "content": PURE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_JAVA_REFINE
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_JAVA_FUNC
        }
]








HISTORY_AGENT_PYTHON = [
        {
            "role": "system",
            "content": AGENT_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_PYTHON_REPORT
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_PYTHON_FUNC
        }
]








HISTORY_LOCATED_PYTHON = [
        {
            "role": "system",
            "content": LOCATED_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_PYTHON_MASK
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_PYTHON_HUNK
        }
]







HISTORY_HYBRID_PYTHON = [
        {
            "role": "system",
            "content": HYBRID_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_PYTHON_MASK
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_PYTHON_FUNC
        }
]








HISTORY_REVERSE_PYTHON = [
        {
            "role": "system",
            "content": REVERSE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_PYTHON_REPORT
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_PYTHON_HUNK
        }
]







HISTORY_PURE_PYTHON = [
        {
            "role": "system",
            "content": PURE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_PYTHON_REFINE
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_PYTHON_FUNC
        }
]








HISTORY_MERGE_CPP = [
        {
            "role": "system",
            "content": MERGE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_MERGE_CPP
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_CPP_FUNC
        }
]








HISTORY_MERGE_JAVA = [
        {
            "role": "system",
            "content": MERGE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_MERGE_JAVA
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_JAVA_FUNC
        }
]







HISTORY_MERGE_PYTHON = [
        {
            "role": "system",
            "content": MERGE_INSTRUCTION
        },
        {
            "role": "user",
            "content": EXAMPLE_INPUT_MERGE_PYTHON
        },
        {
            "role": "assistant",
            "content": EXAMPLE_OUTPUT_PYTHON_FUNC
        }
]





HISTORY_AGENT_LIST = {'cpp': HISTORY_AGENT_CPP, 'java': HISTORY_AGENT_JAVA, 'python3': HISTORY_AGENT_PYTHON}
HISTORY_LOCATED_LIST = {'cpp': HISTORY_LOCATED_CPP, 'java': HISTORY_LOCATED_JAVA, 'python3': HISTORY_LOCATED_PYTHON}
HISTORY_HYBRID_LIST = {'cpp': HISTORY_HYBRID_CPP, 'java': HISTORY_HYBRID_JAVA, 'python3': HISTORY_HYBRID_PYTHON}
HISTORY_REVERSE_LIST = {'cpp': HISTORY_REVERSE_CPP, 'java': HISTORY_REVERSE_JAVA, 'python3': HISTORY_REVERSE_PYTHON}
HISTORY_MERGE_LIST = {'cpp': HISTORY_MERGE_CPP, 'java': HISTORY_MERGE_JAVA, 'python3': HISTORY_MERGE_PYTHON}
HISTORY_PURE_LIST = {'cpp': HISTORY_PURE_CPP, 'java': HISTORY_PURE_JAVA, 'python3': HISTORY_PURE_PYTHON}
