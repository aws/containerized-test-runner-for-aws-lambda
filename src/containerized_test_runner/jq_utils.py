import json
import subprocess


def apply_jq_transform(jq_filter, data, return_all=False):
    """
    Apply jq transformation to data using subprocess
    
    :param jq_filter: jq filter expression
    :param data: input data (dict or other JSON-serializable type)
    :param return_all: if True, return list of all results; if False, return single result
    :return: transformed data (single value or list depending on return_all)
    """
    try:
        # Convert data to JSON string
        input_json = json.dumps(data)
        
        # Run jq command with -c flag to get compact output, one result per line
        result = subprocess.run(
            ['jq', '-c', jq_filter],
            input=input_json,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output - jq returns one result per line
        output_lines = result.stdout.strip().split('\n')
        if not output_lines or (len(output_lines) == 1 and not output_lines[0]):
            return [None] if return_all else None
        
        # Parse each line as JSON
        results = []
        for line in output_lines:
            if line:
                results.append(json.loads(line))
        
        if not results:
            return [None] if return_all else None
        
        return results if return_all else results[0]
    except subprocess.CalledProcessError as e:
        raise Exception(f"jq command failed: {e.stderr}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse jq output: {e}")
