-- cpu.vhd: Simple 8-bit CPU (BrainFuck interpreter)
-- Copyright (C) 2026 Brno University of Technology,
--                    Faculty of Information Technology
-- Author(s): Julius Kundrat <xkundrj00 AT stud.fit.vutbr.cz>
--
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

-- ----------------------------------------------------------------------------
--                        Entity declaration
-- ----------------------------------------------------------------------------
entity cpu is
 port (
   CLK   : in std_logic;  -- hodinovy signal
   RESET : in std_logic;  -- asynchronni reset procesoru
   EN    : in std_logic;  -- povoleni cinnosti procesoru
 
   -- synchronni pamet RAM
   DATA_ADDR  : out std_logic_vector(12 downto 0); -- adresa do pameti
   DATA_WDATA : out std_logic_vector(7 downto 0); -- mem[DATA_ADDR] <- DATA_WDATA pokud DATA_EN='1'
   DATA_RDATA : in std_logic_vector(7 downto 0);  -- DATA_RDATA <- ram[DATA_ADDR] pokud DATA_EN='1'
   DATA_RDWR  : out std_logic;                    -- cteni (1) / zapis (0)
   DATA_EN    : out std_logic;                    -- povoleni cinnosti
   
   -- vstupni port
   IN_DATA   : in std_logic_vector(7 downto 0);   -- IN_DATA <- stav klavesnice pokud IN_VLD='1' a IN_REQ='1'
   IN_VLD    : in std_logic;                      -- data platna
   IN_REQ    : out std_logic;                     -- pozadavek na vstup data
   
   -- vystupni port
   OUT_DATA : out  std_logic_vector(7 downto 0);  -- zapisovana data
   OUT_BUSY : in std_logic;                       -- LCD je zaneprazdnen (1), nelze zapisovat
   OUT_INV  : out std_logic;                      -- pozadavek na aktivaci inverzniho zobrazeni (1)
   OUT_WE   : out std_logic;                      -- LCD <- OUT_DATA pokud OUT_WE='1' a OUT_BUSY='0'

   -- stavove signaly
   READY    : out std_logic;                      -- hodnota 1 znamena, ze byl procesor inicializovan
   DONE     : out std_logic                       -- hodnota 1 znamena, ze procesor ukoncil vykonavani programu (narazil na instrukci halt)
 );
end cpu;


-- ----------------------------------------------------------------------------
--                      Architecture declaration
-- ----------------------------------------------------------------------------
architecture behavioral of cpu is
  type state_type is (

    -- Init phase: find '@'
    S_INIT_LOAD,
    S_INIT_CHECK,

    -- Main fetch states
    S_FETCH,
    S_DECODE,

    --- Instruction execute states ---
    S_PTR_INC,
    S_PTR_DEC,

    S_VAL_INC,
    S_VAL_DEC,
    
    S_WHILE_ST,
    S_WHILE_SKIP,
    S_WHILE_END,

    S_DOWHILE_END,

    --- I/O states ---
    S_PRINT,
    S_INPUT,

    -- Encounter '@' during run
    S_HALT
  );

  type stack_t is array(0 to 15) of std_logic_vector(12 downto 0);

  signal state_reg : state_type;
  signal state_next : state_type;
  signal pc_reg : std_logic_vector(12 downto 0);
  signal pc_next : std_logic_vector(12 downto 0);
  signal ptr_reg : std_logic_vector(12 downto 0);
  signal ptr_next : std_logic_vector(12 downto 0);
  signal sp : natural range 0 to 15;
  signal sp_next : natural range 0 to 15;
  signal scope_ct : integer range 0 to 255;
  signal scope_ct_next : integer range 0 to 255;
  signal stack_push : std_logic;
  signal loop_stack : stack_t;

begin
  process (CLK, RESET)
  begin
    if (RESET = '1') then
      state_reg <= S_INIT_LOAD; -- find '@' after reset
      pc_reg <= (others => '0');
      ptr_reg <= (others => '0');
      sp <= 0;
      scope_ct <= 0;
      loop_stack <= (others => (others => '0'));
    elsif rising_edge(CLK) then
      if EN = '1' then
        state_reg <= state_next;
        pc_reg <= pc_next;
        ptr_reg <= ptr_next;
        sp <= sp_next;
        scope_ct <= scope_ct_next;

        if(stack_push = '1') then
          loop_stack(sp) <= pc_reg + 1;
        end if;

      end if;
    end if;
  end process;

  process (state_reg, pc_reg, ptr_reg, sp, scope_ct, loop_stack, IN_VLD, IN_DATA, DATA_RDATA, OUT_BUSY)
  begin

    state_next <= state_reg;
    pc_next    <= pc_reg;
    ptr_next   <= ptr_reg;
    sp_next <= sp;
    scope_ct_next <= scope_ct;
    stack_push <= '0';

    DATA_ADDR  <= pc_reg;
    DATA_WDATA <= (others => '0');
    DATA_EN    <= '0';
    DATA_RDWR  <= '1';

    IN_REQ     <= '0';
    OUT_DATA   <= (others => '0');
    OUT_WE     <= '0';
    OUT_INV    <= '0';

    READY <= '1';
    DONE <= '0';

    case state_reg is
      when S_INIT_LOAD =>
        READY <= '0';
        DATA_ADDR <= ptr_reg;
        DATA_EN <= '1';
        state_next <= S_INIT_CHECK;
      
      when S_INIT_CHECK =>
        READY <= '0';

        if DATA_RDATA = 64 then
          state_next <= S_FETCH;
        else
          state_next <= S_INIT_LOAD;
        end if;

        ptr_next <= ptr_reg + 1;

      when S_FETCH =>
        DATA_EN <= '1';
        state_next <= S_DECODE;
      
      when S_DECODE =>

        if DATA_RDATA = 40 then    -- execute '('
          stack_push <= '1';
          sp_next    <= sp + 1;
          pc_next    <= pc_reg + 1;
          state_next <= S_FETCH;

        elsif DATA_RDATA = 41 then -- execute ')'
          DATA_ADDR  <= ptr_reg;
          DATA_EN    <= '1';
          state_next <= S_DOWHILE_END;

        elsif DATA_RDATA = 43 then -- execute '+'
          DATA_ADDR <= ptr_reg;
          DATA_EN <= '1';
          state_next <= S_VAL_INC;

        elsif DATA_RDATA = 44 then -- execute ','
          state_next <= S_INPUT;

        elsif DATA_RDATA = 45 then -- execute '-'
          DATA_ADDR <= ptr_reg;
          DATA_EN <= '1';
          state_next <= S_VAL_DEC;

        elsif DATA_RDATA = 46 then -- execute '.'
          DATA_ADDR <= ptr_reg;
          DATA_EN <= '1';
          state_next <= S_PRINT;

        elsif DATA_RDATA = 60 then -- execute '<'
          state_next <= S_PTR_DEC;
        elsif DATA_RDATA = 62 then -- execute '>'
          state_next <= S_PTR_INC;

        elsif DATA_RDATA = 64 then -- execute '@'
          state_next <= S_HALT;
        
        elsif DATA_RDATA = 91 then -- execute '['
          DATA_ADDR <= ptr_reg;
          DATA_EN <= '1';
          state_next <= S_WHILE_ST;
        
        elsif DATA_RDATA = 93 then -- execute ']'
          DATA_ADDR <= ptr_reg;
          DATA_EN <= '1';
          state_next <= S_WHILE_END;
          
        else
          pc_next <= pc_reg + 1; -- ignore unknown instruction
          state_next <= S_FETCH;
        end if;

      when S_PTR_INC =>
        ptr_next <= ptr_reg + 1;
        pc_next <= pc_reg + 1;
        state_next <= S_FETCH;

      when S_PTR_DEC =>
        ptr_next <= ptr_reg - 1;
        pc_next <= pc_reg + 1;
        state_next <= S_FETCH;

      when S_VAL_INC =>
        DATA_ADDR <= ptr_reg;
        DATA_EN <= '1';
        DATA_RDWR <= '0';
        DATA_WDATA <= DATA_RDATA + 1;
        pc_next <= pc_reg + 1;
        state_next <= S_FETCH;
      
      when S_VAL_DEC =>
        DATA_ADDR <= ptr_reg;
        DATA_EN <= '1';
        DATA_RDWR <= '0';
        DATA_WDATA <= DATA_RDATA - 1;
        pc_next <= pc_reg + 1;
        state_next <= S_FETCH;

      when S_INPUT =>
        IN_REQ <= '1';

        if (IN_VLD = '1') then
          DATA_ADDR <= ptr_reg;
          DATA_EN <= '1';
          DATA_RDWR <= '0';
          DATA_WDATA <= IN_DATA;
          pc_next <= pc_reg + 1;
          state_next <= S_FETCH;
        end if;

      when S_PRINT =>
        DATA_ADDR <= ptr_reg;
        DATA_EN <= '1';
        
        if (OUT_BUSY = '0') then
          OUT_DATA <= DATA_RDATA;
          OUT_WE <= '1';
          pc_next <= pc_reg + 1;
          state_next <= S_FETCH;
        end if;
        
      when S_WHILE_ST =>
        if (DATA_RDATA /= 0) then
          stack_push <= '1';
          sp_next <= sp + 1;
          pc_next <= pc_reg + 1;
          state_next <= S_FETCH;
        else
          scope_ct_next <= 1;
          pc_next <= pc_reg + 1;
          DATA_ADDR <= pc_reg + 1;
          DATA_EN <= '1';
          state_next <= S_WHILE_SKIP;
        end if;
      
      when S_WHILE_SKIP =>
        DATA_EN <= '1';
        DATA_ADDR <= pc_reg + 1;
        pc_next <= pc_reg + 1;

        if (DATA_RDATA = 91) then
          scope_ct_next <= scope_ct + 1;
        elsif (DATA_RDATA = 93) then
          if (scope_ct = 1) then
            state_next <= S_FETCH;
          else
            scope_ct_next <= scope_ct - 1;
          end if;
        end if;
      
      when S_WHILE_END =>
        if(DATA_RDATA /= 0) then
          pc_next <= loop_stack(sp - 1);
          state_next <= S_FETCH;
        else
          sp_next <= sp - 1;
          pc_next <= pc_reg + 1;
          state_next <= S_FETCH;
        end if;

      when S_DOWHILE_END =>
        if(DATA_RDATA /= 0) then
          pc_next <= loop_stack(sp - 1);
          state_next <= S_FETCH;
        else
          sp_next <= sp - 1;
          pc_next <= pc_reg + 1;
          state_next <= S_FETCH;
        end if;

      when S_HALT =>
        DONE <= '1';
        state_next <= S_HALT;

    end case;
  end process;
end behavioral;

