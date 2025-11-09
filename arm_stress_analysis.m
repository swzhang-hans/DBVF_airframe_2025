clear
clc

% load json data into struct
%{
data = jsondecode(fileread("aircraft_data.json"));
T = data.W0 * data.T2W / 6;
W = data.arm.W;
L_eff = data.arm.L_eff;
%}
T = 40; W_motor = 0.11*9.81; W_arm = 2.69; R_prop = 21 / 2 * 2.54 / 100; 
L_eff = R_prop + 0.05 ; L = L_eff + 0.05

% material properties
rho = 1700;
E = 6e10; % tensile youngs'modulus
stress_comp_crit = 500e06; % tensile strength
poisson = 0.229;

% loading
T = T - W_motor;
sf = @(x) (T - W_arm + W_arm/L_eff * x);
bm = @(x) -(T-W_arm)*x - 1/2*(W_arm/L_eff)*x^2 + (T*L_eff - 1/2*W_arm*L_eff);
%{
figure
fplot(sf, [0, L_eff])
xlabel('arm')
ylabel('shear force')
figure
fplot(bm, [0, L_eff])
xlabel('arm')
ylabel('bending moment')
%}

% find min radius of arm to avoid comp failure, buckling, crushing
R_out = 0.01:0.002:0.08; % outside radiu
t2R = 1/10;
t = t2R * R_out; % assume a 1/10 ratio as commonly seen
I = pi/4 * (1-(t2R)^4) * R_out.^4; % second moment of area
stress_comp_max = bm(0).*R_out ./ I;
stress_buck_euler_crit = pi^2 * E * I ./ (2*L_eff)^2; % euler buckling, assume clamped for conservatism (clamped 2, ss 1)
stress_buck_crit = pi^2 * E / (12*(1-poisson^2)) .* (t./L_eff).^2; % assume ss for conservatism (clamped 3, ss 12)

R_design1 = R_out(stress_comp_max <= stress_buck_euler_crit);
R_design2 = R_out(stress_comp_max <= stress_buck_crit);
R_design = max(R_design1(1), R_design2(1))
clear R_design1 R_design2

figure
yline(stress_comp_crit/1.2); % safety factor 1.2
hold on
plot(R_out, stress_comp_max)
plot(R_out, stress_buck_euler_crit/1.2)
plot(R_out, stress_buck_crit/1.2)
hold off
legend('critical stress / 1.2', 'max stress', 'citical euler buckling/1.2', 'critical local buckling/1.2')


mass = rho * L * pi * (R_design^2 * (1-(1-t2R)^2))