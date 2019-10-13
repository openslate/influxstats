import inspect
import logging


def get_logger(rewind_stack: int = 1) -> "logging.Logger":
    """
    Returns a logger named based on the path of the function it's called from

    Args:
        rewind_stack: how far back the stack to go to get the function name
    """
    stack = list(inspect.stack())
    frame = stack[rewind_stack].frame

    name = frame.f_globals["__name__"]

    # https://stackoverflow.com/a/2220759
    _, _, _, value_dict = inspect.getargvalues(frame)

    # append the class name if this is being called from an upstream method
    cls = None
    if "self" in value_dict:
        cls = value_dict["self"].__class__
    elif "cls" in value_dict:
        cls = value_dict["cls"]

    if cls:
        class_name = cls.__name__

        name = f"{name}.{class_name}"

    # now tack on the function that this is being called from
    function_name = getattr(frame.f_code, "co_name")
    if function_name:
        if function_name == "<module>":
            logger = get_logger()
            logger.warning(f"global loggers are BAD, name={name}")
        else:
            name = f"{name}.{function_name}"

    return logging.getLogger(name)
