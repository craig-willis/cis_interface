% Initialize input/output channels 
in_channel = CisInterface('CisInput', 'inputB', '%6s\t%d\t%f\n');
out_channel = CisInterface('CisOutput', 'outputB', '%6s\t%d\t%f\n');

flag = true;

% Loop until there is no longer input or the queues are closed
while flag

  % Receive input from input channel
  % If there is an error, the flag will be False.
  [flag, msg] = in_channel.recv();
  if (~flag)
    disp('Model B: No more input.');
    break;
  end;
  name = msg{1};
  count = msg{2};
  size = msg{3};

  % Print received message
  fprintf('Model B: %s, %d, %f\n', name, count, size);

  % Send output to output channel
  % If there is an error, the flag will be False
  flag = out_channel.send(name, count, size);
  if (~flag)
    disp('Model B: Error sending output.');
    break;
  end;
  
end;

exit(0);
