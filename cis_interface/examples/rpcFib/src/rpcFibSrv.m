
function rpcFibSrv(sleeptime)
  
  sleeptime = str2num(sleeptime);
  fprintf('Hello from Matlab rpcFibSrv: sleeptime = %f\n', sleeptime);

  % Create server-side rpc conneciton using model name
  rpc = CisInterface('CisRpcServer', 'rpcFibSrv', '%d', '%d %d');

  % Continue receiving requests until error occurs (the connection is closed
  % by all clients that have connected).
  while 1
    [flag, input] = rpc.recv();
    if (~flag);
      fprintf('rpcFibSrv(M): end of input');
      exit(0);
    end

    % Compute fibonacci number
    fprintf('rpcFibSrv(M): <- input %d', input{1});
    pprev = 0;
    prev = 1;
    result = 1;
    n = 1;
    while n < input{1}
      result = prev + pprev;
      pprev = prev;
      prev = result;
      n = n+1;
    end
    fprintf(' ::: ->(%2d %2d)\n', input{1}, result);

    % Sleep and then send response back
    pause(sleeptime);
    flag = rpc.send(input{1}, result);
    if (~flag);
      fprintf('rpcFibSrv(M): ERROR sending');
      exit(-1);
    end
  end

  disp('Goodbye from Matlab rpcFibSrv');
  exit(0);
end



