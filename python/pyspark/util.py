# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import re
import sys
import traceback
import os
import warnings
import inspect
from py4j.protocol import Py4JJavaError

__all__ = []


def _exception_message(excp):
    """Return the message from an exception as either a str or unicode object.  Supports both
    Python 2 and Python 3.

    >>> msg = "Exception message"
    >>> excp = Exception(msg)
    >>> msg == _exception_message(excp)
    True

    >>> msg = u"unicöde"
    >>> excp = Exception(msg)
    >>> msg == _exception_message(excp)
    True
    """
    if isinstance(excp, Py4JJavaError):
        # 'Py4JJavaError' doesn't contain the stack trace available on the Java side in 'message'
        # attribute in Python 2. We should call 'str' function on this exception in general but
        # 'Py4JJavaError' has an issue about addressing non-ascii strings. So, here we work
        # around by the direct call, '__str__()'. Please see SPARK-23517.
        return excp.__str__()
    if hasattr(excp, "message"):
        return excp.message
    return str(excp)


def _get_argspec(f):
    """
    Get argspec of a function. Supports both Python 2 and Python 3.
    """
    if sys.version_info[0] < 3:
        argspec = inspect.getargspec(f)
    else:
        # `getargspec` is deprecated since python3.0 (incompatible with function annotations).
        # See SPARK-23569.
        argspec = inspect.getfullargspec(f)
    return argspec


def print_exec(stream):
    ei = sys.exc_info()
    traceback.print_exception(ei[0], ei[1], ei[2], None, stream)


class VersionUtils(object):
    """
    Provides utility method to determine Spark versions with given input string.
    """
    @staticmethod
    def majorMinorVersion(sparkVersion):
        """
        Given a Spark version string, return the (major version number, minor version number).
        E.g., for 2.0.1-SNAPSHOT, return (2, 0).

        >>> sparkVersion = "2.4.0"
        >>> VersionUtils.majorMinorVersion(sparkVersion)
        (2, 4)
        >>> sparkVersion = "2.3.0-SNAPSHOT"
        >>> VersionUtils.majorMinorVersion(sparkVersion)
        (2, 3)

        """
        m = re.search(r'^(\d+)\.(\d+)(\..*)?$', sparkVersion)
        if m is not None:
            return (int(m.group(1)), int(m.group(2)))
        else:
            raise ValueError("Spark tried to parse '%s' as a Spark" % sparkVersion +
                             " version string, but it could not find the major and minor" +
                             " version numbers.")


def fail_on_stopiteration(f):
    """
    Wraps the input function to fail on 'StopIteration' by raising a 'RuntimeError'
    prevents silent loss of data when 'f' is used in a for loop in Spark code
    """
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except StopIteration as exc:
            raise RuntimeError(
                "Caught StopIteration thrown from user's code; failing the task",
                exc
            )

    return wrapper


def _warn_pin_thread(name):
    if os.environ.get("PYSPARK_PIN_THREAD", "false").lower() == "true":
        msg = (
            "PYSPARK_PIN_THREAD feature is enabled. "
            "However, note that it cannot inherit the local properties from the parent thread "
            "although it isolates each thread on PVM and JVM with its own local properties. "
            "\n"
            "To work around this, you should manually copy and set the local properties from "
            "the parent thread to the child thread when you create another thread.")
    else:
        msg = (
            "Currently, '%s' (set to local properties) with multiple threads does "
            "not properly work. "
            "\n"
            "Internally threads on PVM and JVM are not synced, and JVM thread can be reused "
            "for multiple threads on PVM, which fails to isolate local properties for each "
            "thread on PVM. "
            "\n"
            "To work around this, you can set PYSPARK_PIN_THREAD to true (see SPARK-22340). "
            "However, note that it cannot inherit the local properties from the parent thread "
            "although it isolates each thread on PVM and JVM with its own local properties. "
            "\n"
            "To work around this, you should manually copy and set the local properties from "
            "the parent thread to the child thread when you create another thread." % name)
    warnings.warn(msg, UserWarning)


def _print_missing_jar(lib_name, pkg_name, jar_name, spark_version):
    print("""
________________________________________________________________________________________________

  Spark %(lib_name)s libraries not found in class path. Try one of the following.

  1. Include the %(lib_name)s library and its dependencies with in the
     spark-submit command as

     $ bin/spark-submit --packages org.apache.spark:spark-%(pkg_name)s:%(spark_version)s ...

  2. Download the JAR of the artifact from Maven Central http://search.maven.org/,
     Group Id = org.apache.spark, Artifact Id = spark-%(jar_name)s, Version = %(spark_version)s.
     Then, include the jar in the spark-submit command as

     $ bin/spark-submit --jars <spark-%(jar_name)s.jar> ...

________________________________________________________________________________________________

""" % {
        "lib_name": lib_name,
        "pkg_name": pkg_name,
        "jar_name": jar_name,
        "spark_version": spark_version
    })


def _parse_memory(s):
    """
    Parse a memory string in the format supported by Java (e.g. 1g, 200m) and
    return the value in MiB

    >>> _parse_memory("256m")
    256
    >>> _parse_memory("2g")
    2048
    """
    units = {'g': 1024, 'm': 1, 't': 1 << 20, 'k': 1.0 / 1024}
    if s[-1].lower() not in units:
        raise ValueError("invalid format: " + s)
    return int(float(s[:-1]) * units[s[-1].lower()])

if __name__ == "__main__":
    import doctest
    (failure_count, test_count) = doctest.testmod()
    if failure_count:
        sys.exit(-1)
