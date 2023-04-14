#
#  MIT License
#
#  (C) Copyright 2023 Hewlett Packard Enterprise Development LP
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
#  OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#  ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#  OTHER DEALINGS IN THE SOFTWARE.
#

import logging
from logging.handlers import RotatingFileHandler


class Logger(logging.Logger):
    """
    Inherits from logging.Logger, configuring custom settings on
    initialization.
    """

    def __init__(
            self,
            module_name: str,
            log_level: int = logging.INFO
    ) -> None:
        """
        :param module_name: Pass __name__ here or whatever name you want to
                            define the Logger as.
        :param log_level: Level of logging (default: INFO).
        """
        super(Logger, self).__init__(module_name, log_level)
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)-8s | %(name)-20s | %(message)s'
        )
        formatter.datefmt = '%b %d %H:%M:%S'
        # TODO: Write to a system path other than the working directory.
        handler = RotatingFileHandler('crucible.log')
        handler.setFormatter(formatter)
        self.addHandler(handler)
