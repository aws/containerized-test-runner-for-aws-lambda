import jq


def apply_jq_transform(jq_filter, data, return_all=False):
    """
    Apply jq transformation to data using the jq Python library
    
    :param jq_filter: jq filter expression
    :param data: input data (dict or other JSON-serializable type)
    :param return_all: if True, return list of all results; if False, return single result
    :return: transformed data (single value or list depending on return_all)
    """
    try:
        # Compile the jq filter
        compiled_filter = jq.compile(jq_filter)
        
        if return_all:
            # Return all results as a list
            results = list(compiled_filter.input(data).all())
            # Filter out None values
            results = [r for r in results if r is not None]
            return results if results else [None]
        else:
            # Return the first result
            return compiled_filter.input(data).first()
    except Exception as e:
        raise Exception(f"jq transformation failed: {e}")
