clear
clc

% load data
W0 = 8 * 9.81; 
R = 21 * 2.54 / 100 + 0.05 + 0.2;
L = (R - 0.3) / sqrt(3)

% material properties
rho = 1700;
E = 9.3e10; % youngs'modulus
stress_comp_crit = 920e06; % compressive strength
poisson = 0.5;

% loading conditions
W = W0 / 6 * 2

% find min radius of arm to avoid comp failure, buckling, crushing
R_out = 0.006:0.002:0.02; % outside radiu
t2R = 1/10;
t = t2R * R_out; % assume a 1/10 ratio as commonly seen
area = pi * (R_out.^2 - (R_out - t).^2);
I = pi/4 * (R_out.^4 - (R_out - t).^4); % second moment of area
stress_comp_max = W ./ area
stress_buck_euler_crit = pi^2 * E * I ./ (2*L)^2 ./ area; % euler buckling, assume clamped for conservatism (clamped 2, ss 1)
stress_buck_crit = pi^2 * E / (3*(1-poisson^2)) .* (t./L).^2 % assume ss for conservatism (clamped 3, ss 12)


R_design1 = R_out(stress_comp_max <= stress_buck_euler_crit/1.2);
R_design2 = R_out(stress_comp_max <= stress_buck_crit/1.2);
R_design = max(R_design1(1), R_design2(1))
clear R_design1 R_design2


figure
yline(stress_comp_crit/1.2, 'linewidth', 1); % safety factor 1.1
hold on
plot(R_out, stress_comp_max, 'linewidth', 1)
plot(R_out, stress_buck_euler_crit/1.2, 'linewidth', 1)
plot(R_out, stress_buck_crit/1.2,'linewidth', 1)
hold off
legend('critical stress / 1.2', 'max stress', 'citical euler buckling / 1.2', 'critical local buckling / 1.2')


mass = rho * L * pi * (R_design^2 * (1-(1-t2R)^2))